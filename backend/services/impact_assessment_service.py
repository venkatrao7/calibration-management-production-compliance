
import json
from datetime import datetime

try:
    from backend.db import get_db_connection
except ModuleNotFoundError:
    from db import get_db_connection


VALID_CATEGORIES = {
    "NO_IMPACT",
    "PRODUCT_HOLD",
    "REWORK_REQUIRED",
    "RECALL_REQUIRED",
    "INVESTIGATION_REQUIRED"
}


def parse_datetime(value, field):
    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value).replace("T", " "))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field} datetime")


def list_assessments(connection, search=None, status=None, limit=100, offset=0):
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            term = f"%{search}%"
            conditions.append("""
                (ia.assessment_id LIKE %s
                 OR ia.calibration_id LIKE %s
                 OR ia.asset_id LIKE %s
                 OR ia.work_order_id LIKE %s)
            """)
            params.extend([term, term, term, term])

        if status:
            if status not in {"DRAFT", "COMPLETED"}:
                raise ValueError("Invalid assessment status")
            conditions.append("ia.assessment_status = %s")
            params.append(status)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(
            f"""
            SELECT
                ia.*,
                a.asset_name,
                ce.result AS calibration_result
            FROM impact_assessment ia
            JOIN asset a ON a.asset_id = ia.asset_id
            JOIN calibration_event ce
                ON ce.calibration_id = ia.calibration_id
                AND ce.asset_id = ia.asset_id
            {where}
            ORDER BY ia.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset]
        )

        records = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM impact_assessment ia
            {where}
            """,
            params
        )

        total = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS draft_total
            FROM impact_assessment
            WHERE assessment_status = 'DRAFT'
        """)

        draft_total = cursor.fetchone()["draft_total"]

        return {
            "total": total,
            "draft_total": draft_total,
            "records": records
        }

    finally:
        cursor.close()


def create_assessment(data, changed_by="System"):
    calibration_id = data.get("calibration_id")
    asset_id = data.get("asset_id")
    work_order_id = data.get("work_order_id")

    if not calibration_id or not asset_id or not work_order_id:
        raise ValueError(
            "calibration_id, asset_id and work_order_id are required"
        )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT calibration_id, asset_id, result
            FROM calibration_event
            WHERE calibration_id = %s AND asset_id = %s
            FOR UPDATE
            """,
            (calibration_id, asset_id)
        )

        calibration = cursor.fetchone()

        if not calibration:
            raise ValueError("Calibration event does not belong to this asset")

        if calibration["result"] != "FAIL":
            raise ValueError("Impact assessment requires a failed calibration")

        cursor.execute(
            """
            SELECT work_order_id, asset_id, calibration_id, work_type
            FROM work_order
            WHERE work_order_id = %s
            FOR UPDATE
            """,
            (work_order_id,)
        )

        work_order = cursor.fetchone()

        if not work_order:
            raise ValueError("Corrective work order does not exist")

        if (
            work_order["asset_id"] != asset_id
            or work_order["calibration_id"] != calibration_id
            or work_order["work_type"] != "CORRECTIVE_ACTION"
        ):
            raise ValueError(
                "Work order must be a corrective action for the same asset "
                "and failed calibration"
            )

        assessment_id = f"IA-{calibration_id}"

        cursor.execute(
            """
            SELECT assessment_id
            FROM impact_assessment
            WHERE assessment_id = %s
            """,
            (assessment_id,)
        )

        if cursor.fetchone():
            raise ValueError("An assessment already exists for this calibration")

        cursor.execute(
            """
            INSERT INTO impact_assessment (
                assessment_id,
                calibration_id,
                asset_id,
                work_order_id,
                assessment_status,
                notes
            )
            VALUES (%s, %s, %s, %s, 'DRAFT', %s)
            """,
            (
                assessment_id,
                calibration_id,
                asset_id,
                work_order_id,
                data.get("notes")
            )
        )

        new_values = {
            "assessment_id": assessment_id,
            "calibration_id": calibration_id,
            "asset_id": asset_id,
            "work_order_id": work_order_id,
            "assessment_status": "DRAFT",
            "notes": data.get("notes")
        }

        cursor.execute(
            """
            INSERT INTO audit_record (
                entity_name, entity_id, action,
                old_values, new_values, changed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "impact_assessment",
                assessment_id,
                "INSERT",
                None,
                json.dumps(new_values),
                changed_by
            )
        )

        connection.commit()

        return {
            "assessment_id": assessment_id,
            "message": "Impact assessment draft created successfully"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def complete_assessment(assessment_id, data, changed_by="System"):
    category = data.get("impact_category")
    disposition = data.get("disposition")
    assessed_by = data.get("assessed_by")

    if category not in VALID_CATEGORIES:
        raise ValueError("A valid impact_category is required")

    if not disposition or not str(disposition).strip():
        raise ValueError("Disposition is required")

    if not assessed_by or not str(assessed_by).strip():
        raise ValueError("assessed_by is required")

    assessed_at = parse_datetime(
        data.get("assessed_at") or datetime.now(),
        "assessed_at"
    )

    affected_from = data.get("affected_from")
    affected_to = data.get("affected_to")

    if affected_from:
        affected_from = parse_datetime(affected_from, "affected_from")

    if affected_to:
        affected_to = parse_datetime(affected_to, "affected_to")

    if affected_from and affected_to and affected_to < affected_from:
        raise ValueError("affected_to cannot be earlier than affected_from")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM impact_assessment
            WHERE assessment_id = %s
            FOR UPDATE
            """,
            (assessment_id,)
        )

        old = cursor.fetchone()

        if not old:
            raise ValueError("Impact assessment not found")

        if old["assessment_status"] != "DRAFT":
            raise ValueError("Only DRAFT assessments can be completed")

        cursor.execute(
            """
            UPDATE impact_assessment
            SET assessment_status = 'COMPLETED',
                impact_category = %s,
                affected_from = %s,
                affected_to = %s,
                disposition = %s,
                notes = %s,
                assessed_by = %s,
                assessed_at = %s
            WHERE assessment_id = %s
            """,
            (
                category,
                affected_from,
                affected_to,
                disposition,
                data.get("notes", old["notes"]),
                assessed_by,
                assessed_at,
                assessment_id
            )
        )

        new_values = {
            "assessment_status": "COMPLETED",
            "impact_category": category,
            "affected_from": affected_from.isoformat() if affected_from else None,
            "affected_to": affected_to.isoformat() if affected_to else None,
            "disposition": disposition,
            "notes": data.get("notes", old["notes"]),
            "assessed_by": assessed_by,
            "assessed_at": assessed_at.isoformat()
        }

        cursor.execute(
            """
            INSERT INTO audit_record (
                entity_name, entity_id, action,
                old_values, new_values, changed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "impact_assessment",
                assessment_id,
                "STATUS_CHANGE",
                json.dumps({
                    "assessment_status": old["assessment_status"]
                }),
                json.dumps(new_values),
                changed_by
            )
        )

        connection.commit()

        return {
            "assessment_id": assessment_id,
            "message": "Impact assessment completed successfully"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
