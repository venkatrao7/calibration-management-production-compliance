
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
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD HH:MM:SS format"
        )


def list_production_uses(connection, search=None, limit=100, offset=0):
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                pu.use_id,
                pu.asset_id,
                a.asset_name,
                pu.use_start,
                pu.use_end,
                pu.production_line,
                pu.exception_reference,
                ee.status AS extension_status
            FROM production_use pu
            JOIN asset a ON a.asset_id = pu.asset_id
            LEFT JOIN emergency_extension ee
                ON ee.extension_reference = pu.exception_reference
            WHERE (
                %s IS NULL
                OR pu.use_id LIKE %s
                OR pu.asset_id LIKE %s
                OR a.asset_name LIKE %s
                OR pu.production_line LIKE %s
            )
            ORDER BY pu.use_start DESC, pu.use_id
            LIMIT %s OFFSET %s
        """

        term = f"%{search}%" if search else None

        cursor.execute(
            query,
            (term, term, term, term, term, limit, offset)
        )
        records = cursor.fetchall()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM production_use pu
            JOIN asset a ON a.asset_id = pu.asset_id
            WHERE (
                %s IS NULL
                OR pu.use_id LIKE %s
                OR pu.asset_id LIKE %s
                OR a.asset_name LIKE %s
                OR pu.production_line LIKE %s
            )
            """,
            (term, term, term, term, term)
        )

        total = cursor.fetchone()["total"]

        return {"total": total, "records": records}

    finally:
        cursor.close()


def create_production_use(data, changed_by="System"):
    required = ["asset_id", "use_start"]

    for field in required:
        if not data.get(field):
            raise ValueError(f"{field} is required")

    asset_id = str(data["asset_id"]).strip()
    use_start = _parse_datetime(data["use_start"], "use_start")

    use_end = data.get("use_end")
    if use_end:
        use_end = _parse_datetime(use_end, "use_end")
        if use_end < use_start:
            raise ValueError("use_end cannot be earlier than use_start")

    production_line = data.get("production_line")
    exception_reference = data.get("exception_reference") or None

    use_id = (
        f"USE-{asset_id}-{use_start.strftime('%Y%m%d%H%M%S')}"
    )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT asset_id, status FROM asset WHERE asset_id = %s FOR UPDATE",
            (asset_id,)
        )
        asset = cursor.fetchone()

        if not asset:
            raise ValueError("Asset does not exist")

        if asset["status"] != "ACTIVE":
            raise ValueError("Production use cannot be recorded for an inactive asset")

        if exception_reference:
            cursor.execute(
                """
                SELECT extension_reference
                FROM emergency_extension
                WHERE extension_reference = %s
                  AND asset_id = %s
                  AND status = 'APPROVED'
                  AND valid_from <= %s
                  AND valid_to >= %s
                """,
                (
                    exception_reference,
                    asset_id,
                    use_start,
                    use_end or use_start
                )
            )

            if not cursor.fetchone():
                raise ValueError(
                    "Emergency extension is not approved or is not valid "
                    "for this asset and usage period"
                )

        cursor.execute(
            """
            INSERT INTO production_use (
                use_id,
                asset_id,
                use_start,
                use_end,
                production_line,
                exception_reference
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                use_id,
                asset_id,
                use_start,
                use_end,
                production_line,
                exception_reference
            )
        )

        new_values = {
            "use_id": use_id,
            "asset_id": asset_id,
            "use_start": use_start.isoformat(),
            "use_end": use_end.isoformat() if use_end else None,
            "production_line": production_line,
            "exception_reference": exception_reference
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
                "production_use",
                use_id,
                "INSERT",
                None,
                json.dumps(new_values),
                changed_by
            )
        )

        connection.commit()

        return {
            "use_id": use_id,
            "message": "Production use recorded successfully"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
