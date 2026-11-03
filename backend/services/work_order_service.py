
import json
from datetime import datetime

try:
    from backend.db import get_db_connection
except ModuleNotFoundError:
    from db import get_db_connection


def _parse_datetime(value, field_name):
    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value).replace("T", " "))
    except (ValueError, TypeError):
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD HH:MM:SS format"
        )


def list_work_orders(connection, search=None, status=None, limit=100, offset=0):
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            term = f"%{search}%"
            conditions.append("""
                (wo.work_order_id LIKE %s
                 OR wo.asset_id LIKE %s
                 OR a.asset_name LIKE %s
                 OR wo.calibration_id LIKE %s)
            """)
            params.extend([term, term, term, term])

        if status:
            conditions.append("wo.status = %s")
            params.append(status)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                wo.work_order_id,
                wo.asset_id,
                a.asset_name,
                wo.calibration_id,
                wo.work_type,
                wo.start_date,
                wo.end_date,
                wo.downtime_minutes,
                wo.status,
                wo.description
            FROM work_order wo
            JOIN asset a ON a.asset_id = wo.asset_id
            {where_clause}
            ORDER BY wo.start_date DESC, wo.work_order_id DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset]
        )

        records = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM work_order wo
            JOIN asset a ON a.asset_id = wo.asset_id
            {where_clause}
            """,
            params
        )

        total = cursor.fetchone()["total"]

        return {"total": total, "records": records}

    finally:
        cursor.close()


def create_work_order(data, changed_by="System"):
    required = ["asset_id", "work_type", "start_date"]

    for field in required:
        if not data.get(field):
            raise ValueError(f"{field} is required")

    asset_id = str(data["asset_id"]).strip()
    work_type = str(data["work_type"]).strip()
    start_date = _parse_datetime(data["start_date"], "start_date")

    if not work_type:
        raise ValueError("work_type cannot be empty")

    end_date = data.get("end_date")
    if end_date:
        end_date = _parse_datetime(end_date, "end_date")
        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date")

    downtime_minutes = int(data.get("downtime_minutes") or 0)

    if downtime_minutes < 0:
        raise ValueError("downtime_minutes cannot be negative")

    calibration_id = data.get("calibration_id") or None
    description = data.get("description")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT asset_id FROM asset WHERE asset_id = %s FOR UPDATE",
            (asset_id,)
        )

        if not cursor.fetchone():
            raise ValueError("Asset does not exist")

        # Ensure the selected calibration belongs to this asset.
        if calibration_id:
            cursor.execute(
                """
                SELECT calibration_id, result
                FROM calibration_event
                WHERE calibration_id = %s AND asset_id = %s
                """,
                (calibration_id, asset_id)
            )

            calibration = cursor.fetchone()

            if not calibration:
                raise ValueError(
                    "Calibration event does not belong to the selected asset"
                )

        year = start_date.year
        prefix = f"WO-{year}-"

        cursor.execute(
            """
            SELECT work_order_id
            FROM work_order
            WHERE work_order_id LIKE %s
            ORDER BY work_order_id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (prefix + "%",)
        )

        last_order = cursor.fetchone()

        sequence = (
            int(last_order["work_order_id"].split("-")[-1]) + 1
            if last_order else 1
        )

        work_order_id = f"{prefix}{sequence:06d}"

        cursor.execute(
            """
            INSERT INTO work_order (
                work_order_id,
                asset_id,
                calibration_id,
                work_type,
                start_date,
                end_date,
                downtime_minutes,
                status,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN', %s)
            """,
            (
                work_order_id,
                asset_id,
                calibration_id,
                work_type,
                start_date,
                end_date,
                downtime_minutes,
                description
            )
        )

        new_values = {
            "work_order_id": work_order_id,
            "asset_id": asset_id,
            "calibration_id": calibration_id,
            "work_type": work_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "downtime_minutes": downtime_minutes,
            "status": "OPEN",
            "description": description
        }

        cursor.execute(
            """
            INSERT INTO audit_record (
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                changed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "work_order",
                work_order_id,
                "INSERT",
                None,
                json.dumps(new_values),
                changed_by
            )
        )

        connection.commit()

        return {
            "work_order_id": work_order_id,
            "message": "Work order created successfully"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

def update_work_order_status(work_order_id, data, changed_by="System"):
    new_status = data.get("status")

    valid_transitions = {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set()
    }

    if new_status not in {
        "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"
    }:
        raise ValueError("Invalid work order status")

    end_date = data.get("end_date")
    downtime_minutes = data.get("downtime_minutes")

    if end_date:
        end_date = _parse_datetime(end_date, "end_date")

    if downtime_minutes is not None:
        downtime_minutes = int(downtime_minutes)
        if downtime_minutes < 0:
            raise ValueError("Downtime cannot be negative")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM work_order
            WHERE work_order_id = %s
            FOR UPDATE
            """,
            (work_order_id,)
        )

        old = cursor.fetchone()

        if not old:
            raise ValueError("Work order not found")

        old_status = old["status"]

        if new_status not in valid_transitions[old_status]:
            raise ValueError(
                f"Status transition from {old_status} to "
                f"{new_status} is not allowed"
            )

        if new_status == "COMPLETED" and not end_date:
            raise ValueError(
                "end_date is required when completing a work order"
            )

        if end_date and end_date < old["start_date"]:
            raise ValueError("end_date cannot be earlier than start_date")

        final_end_date = end_date or old["end_date"]
        final_downtime = (
            downtime_minutes
            if downtime_minutes is not None
            else old["downtime_minutes"]
        )

        cursor.execute(
            """
            UPDATE work_order
            SET status = %s,
                end_date = %s,
                downtime_minutes = %s
            WHERE work_order_id = %s
            """,
            (
                new_status,
                final_end_date,
                final_downtime,
                work_order_id
            )
        )

        old_values = {
            "status": old_status,
            "end_date": (
                old["end_date"].isoformat()
                if old["end_date"] else None
            ),
            "downtime_minutes": old["downtime_minutes"]
        }

        new_values = {
            "status": new_status,
            "end_date": (
                final_end_date.isoformat()
                if final_end_date else None
            ),
            "downtime_minutes": final_downtime
        }

        cursor.execute(
            """
            INSERT INTO audit_record (
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                changed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "work_order",
                work_order_id,
                "STATUS_CHANGE",
                json.dumps(old_values),
                json.dumps(new_values),
                changed_by
            )
        )

        connection.commit()

        return {
            "work_order_id": work_order_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": "Work order status updated successfully"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
