
import json
from datetime import date


VALID_PLAN_STATUSES = {"ACTIVE", "INACTIVE"}


def write_audit(cursor, entity_name, entity_id, action,
                old_values, new_values, changed_by):
    cursor.execute(
        """
        INSERT INTO audit_record (
            entity_name, entity_id, action,
            old_values, new_values, changed_by
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            entity_name,
            str(entity_id),
            action,
            json.dumps(old_values, default=str) if old_values else None,
            json.dumps(new_values, default=str) if new_values else None,
            changed_by
        )
    )


def list_calibration_plans(
    connection, search=None, status=None, limit=100, offset=0
):
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            conditions.append(
                "(CAST(cp.plan_id AS CHAR) LIKE %s "
                "OR cp.asset_id LIKE %s "
                "OR a.asset_name LIKE %s)"
            )
            term = f"%{search}%"
            params.extend([term, term, term])

        if status:
            if status not in VALID_PLAN_STATUSES:
                raise ValueError("Invalid calibration plan status.")
            conditions.append("cp.status = %s")
            params.append(status)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                cp.plan_id,
                cp.asset_id,
                a.asset_name,
                cp.interval_days,
                cp.effective_from,
                cp.effective_to,
                cp.status,
                cp.created_at
            FROM calibration_plan cp
            JOIN asset a ON a.asset_id = cp.asset_id
            {where_clause}
            ORDER BY cp.plan_id
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )
        plans = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM calibration_plan cp
            JOIN asset a ON a.asset_id = cp.asset_id
            {where_clause}
            """,
            tuple(params)
        )
        total = cursor.fetchone()["total"]

        return {"total": total, "plans": plans}

    finally:
        cursor.close()


def get_calibration_plan(connection, plan_id):
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                cp.plan_id,
                cp.asset_id,
                a.asset_name,
                cp.interval_days,
                cp.effective_from,
                cp.effective_to,
                cp.status,
                cp.created_at
            FROM calibration_plan cp
            JOIN asset a ON a.asset_id = cp.asset_id
            WHERE cp.plan_id = %s
            """,
            (plan_id,)
        )
        return cursor.fetchone()

    finally:
        cursor.close()


def create_calibration_plan(connection, data):
    asset_id = data.get("asset_id")
    interval_days = data.get("interval_days")
    effective_from = data.get("effective_from")
    effective_to = data.get("effective_to")
    status = data.get("status", "ACTIVE")
    changed_by = data.get("changed_by", "SYSTEM_USER")

    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id is required.")

    if (
        isinstance(interval_days, bool)
        or not isinstance(interval_days, int)
        or interval_days <= 0
    ):
        raise ValueError("interval_days must be a positive integer.")

    if status not in VALID_PLAN_STATUSES:
        raise ValueError("Status must be ACTIVE or INACTIVE.")

    try:
        effective_from = date.fromisoformat(effective_from)
        effective_to = (
            date.fromisoformat(effective_to)
            if effective_to else None
        )
    except (ValueError, TypeError):
        raise ValueError("Dates must use YYYY-MM-DD format.")

    if effective_to and effective_to < effective_from:
        raise ValueError("effective_to cannot be before effective_from.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT asset_id, asset_name, status
            FROM asset
            WHERE asset_id = %s
            FOR UPDATE
            """,
            (asset_id.strip(),)
        )
        asset = cursor.fetchone()

        if not asset:
            raise ValueError("Asset does not exist.")

        if asset["status"] != "ACTIVE":
            raise ValueError("Cannot create a plan for an inactive asset.")

        cursor.execute(
            """
            SELECT plan_id
            FROM calibration_plan
            WHERE asset_id = %s
              AND status = 'ACTIVE'
              AND effective_from <= COALESCE(%s, '9999-12-31')
              AND (effective_to IS NULL OR effective_to >= %s)
            LIMIT 1
            """,
            (asset_id.strip(), effective_to, effective_from)
        )

        if cursor.fetchone():
            raise ValueError(
                "An active plan already overlaps this effective period."
            )

        cursor.execute(
            """
            INSERT INTO calibration_plan (
                asset_id, interval_days,
                effective_from, effective_to, status
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                asset_id.strip(),
                interval_days,
                effective_from,
                effective_to,
                status
            )
        )

        plan_id = cursor.lastrowid

        new_values = {
            "plan_id": plan_id,
            "asset_id": asset_id.strip(),
            "interval_days": interval_days,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "status": status
        }

        write_audit(
            cursor,
            "calibration_plan",
            plan_id,
            "INSERT",
            None,
            new_values,
            changed_by
        )

        connection.commit()

        return get_calibration_plan(connection, plan_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

# ============================================================
# CALIBRATION EVENT MANAGEMENT
# ============================================================

from datetime import date, timedelta


VALID_EVENT_STATUSES = {"SCHEDULED", "COMPLETED", "CANCELLED"}
VALID_CALIBRATION_RESULTS = {"PASS", "FAIL"}


def _parse_event_date(value, field_name):
    """Validate and convert an ISO date string."""
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")


def _get_calibration_event(cursor, calibration_id):
    cursor.execute(
        """
        SELECT
            ce.calibration_id,
            ce.asset_id,
            a.asset_name,
            ce.plan_id,
            ce.supplier_id,
            ce.scheduled_date,
            ce.calibration_date,
            ce.due_date,
            ce.result,
            ce.measured_value,
            ce.performed_by,
            ce.status,
            ce.created_at,
            cp.interval_days
        FROM calibration_event ce
        JOIN asset a ON a.asset_id = ce.asset_id
        LEFT JOIN calibration_plan cp ON cp.plan_id = ce.plan_id
        WHERE ce.calibration_id = %s
        """,
        (calibration_id,)
    )
    return cursor.fetchone()


def get_calibration_event(connection, calibration_id):
    cursor = connection.cursor(dictionary=True)
    try:
        return _get_calibration_event(cursor, calibration_id)
    finally:
        cursor.close()


def list_calibration_events(
    connection,
    search=None,
    status=None,
    result=None,
    limit=100,
    offset=0
):
    if status and status not in VALID_EVENT_STATUSES:
        raise ValueError("Invalid calibration event status.")

    if result and result not in VALID_CALIBRATION_RESULTS:
        raise ValueError("Result must be PASS or FAIL.")

    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            term = f"%{search}%"
            conditions.append(
                """
                (
                    ce.calibration_id LIKE %s
                    OR ce.asset_id LIKE %s
                    OR a.asset_name LIKE %s
                )
                """
            )
            params.extend([term, term, term])

        if status:
            conditions.append("ce.status = %s")
            params.append(status)

        if result:
            conditions.append("ce.result = %s")
            params.append(result)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                ce.calibration_id,
                ce.asset_id,
                a.asset_name,
                ce.plan_id,
                ce.supplier_id,
                ce.scheduled_date,
                ce.calibration_date,
                ce.due_date,
                ce.result,
                ce.measured_value,
                ce.performed_by,
                ce.status,
                ce.created_at
            FROM calibration_event ce
            JOIN asset a ON a.asset_id = ce.asset_id
            {where_clause}
            ORDER BY ce.created_at DESC, ce.calibration_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )
        events = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM calibration_event ce
            JOIN asset a ON a.asset_id = ce.asset_id
            {where_clause}
            """,
            tuple(params)
        )
        total = cursor.fetchone()["total"]

        return {"total": total, "events": events}

    finally:
        cursor.close()


def schedule_calibration(connection, data):
    asset_id = data.get("asset_id")
    scheduled_date = _parse_event_date(
        data.get("scheduled_date"),
        "scheduled_date"
    )

    plan_id = data.get("plan_id")
    supplier_id = data.get("supplier_id")
    changed_by = data.get("changed_by", "SYSTEM_USER")

    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id is required.")

    asset_id = asset_id.strip()

    if plan_id in ("", None):
        plan_id = None
    else:
        try:
            plan_id = int(plan_id)
        except (ValueError, TypeError):
            raise ValueError("plan_id must be a valid integer.")

    if supplier_id in ("", None):
        supplier_id = None
    else:
        try:
            supplier_id = int(supplier_id)
        except (ValueError, TypeError):
            raise ValueError("supplier_id must be a valid integer.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        # Lock the asset row to serialize ID generation for this asset.
        cursor.execute(
            """
            SELECT asset_id, asset_name, status
            FROM asset
            WHERE asset_id = %s
            FOR UPDATE
            """,
            (asset_id,)
        )
        asset = cursor.fetchone()

        if not asset:
            raise ValueError("Asset does not exist.")

        if asset["status"] != "ACTIVE":
            raise ValueError("Cannot schedule calibration for an inactive asset.")

        # Find the effective active plan, or validate the supplied plan.
        if plan_id is None:
            cursor.execute(
                """
                SELECT plan_id, interval_days
                FROM calibration_plan
                WHERE asset_id = %s
                  AND status = 'ACTIVE'
                  AND effective_from <= %s
                  AND (effective_to IS NULL OR effective_to >= %s)
                ORDER BY effective_from DESC, plan_id DESC
                LIMIT 1
                """,
                (asset_id, scheduled_date, scheduled_date)
            )
        else:
            cursor.execute(
                """
                SELECT plan_id, interval_days
                FROM calibration_plan
                WHERE plan_id = %s
                  AND asset_id = %s
                  AND status = 'ACTIVE'
                  AND effective_from <= %s
                  AND (effective_to IS NULL OR effective_to >= %s)
                """,
                (plan_id, asset_id, scheduled_date, scheduled_date)
            )

        plan = cursor.fetchone()

        if not plan:
            raise ValueError(
                "No active calibration plan is effective for this asset "
                "on the scheduled date."
            )

        plan_id = plan["plan_id"]

        # Generate the next ID for this asset and scheduled year.
        year = scheduled_date.year
        prefix = f"CAL-{asset_id}-{year}-"

        cursor.execute(
            """
            SELECT calibration_id
            FROM calibration_event
            WHERE calibration_id LIKE %s
            ORDER BY calibration_id DESC
            LIMIT 1
            """,
            (prefix + "%",)
        )
        last_event = cursor.fetchone()

        if last_event:
            last_number = int(last_event["calibration_id"].rsplit("-", 1)[1])
        else:
            last_number = 0

        calibration_id = f"{prefix}{last_number + 1:06d}"

        cursor.execute(
            """
            INSERT INTO calibration_event (
                calibration_id,
                asset_id,
                plan_id,
                supplier_id,
                scheduled_date,
                calibration_date,
                due_date,
                result,
                status
            )
            VALUES (%s, %s, %s, %s, %s, NULL, NULL, NULL, 'SCHEDULED')
            """,
            (
                calibration_id,
                asset_id,
                plan_id,
                supplier_id,
                scheduled_date
            )
        )

        new_values = {
            "calibration_id": calibration_id,
            "asset_id": asset_id,
            "plan_id": plan_id,
            "supplier_id": supplier_id,
            "scheduled_date": scheduled_date,
            "status": "SCHEDULED"
        }

        write_audit(
            cursor,
            "calibration_event",
            calibration_id,
            "INSERT",
            None,
            new_values,
            changed_by
        )

        connection.commit()
        return get_calibration_event(connection, calibration_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def complete_calibration(connection, calibration_id, data):
    calibration_date = _parse_event_date(
        data.get("calibration_date"),
        "calibration_date"
    )

    result = data.get("result")
    measured_value = data.get("measured_value")
    performed_by = data.get("performed_by")
    changed_by = data.get("changed_by", "SYSTEM_USER")

    if result not in VALID_CALIBRATION_RESULTS:
        raise ValueError("Result must be PASS or FAIL.")

    if not isinstance(performed_by, str) or not performed_by.strip():
        raise ValueError("performed_by is required.")

    if measured_value in ("", None):
        measured_value = None
    else:
        try:
            measured_value = float(measured_value)
        except (ValueError, TypeError):
            raise ValueError("measured_value must be numeric.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT *
            FROM calibration_event
            WHERE calibration_id = %s
            FOR UPDATE
            """,
            (calibration_id,)
        )
        event = cursor.fetchone()

        if not event:
            raise ValueError("Calibration event does not exist.")

        if event["status"] != "SCHEDULED":
            raise ValueError(
                "Only scheduled calibration events can be completed."
            )

        # Lock and validate the linked plan.
        cursor.execute(
            """
            SELECT interval_days, effective_from, effective_to, status
            FROM calibration_plan
            WHERE plan_id = %s
              AND asset_id = %s
            FOR UPDATE
            """,
            (event["plan_id"], event["asset_id"])
        )
        plan = cursor.fetchone()

        if not plan or plan["status"] != "ACTIVE":
            raise ValueError("The linked calibration plan is not active.")

        if (
            calibration_date < plan["effective_from"]
            or (
                plan["effective_to"]
                and calibration_date > plan["effective_to"]
            )
        ):
            raise ValueError(
                "The linked calibration plan is not effective "
                "on the actual calibration date."
            )

        due_date = calibration_date + timedelta(
            days=plan["interval_days"]
        )

        old_values = {
            "status": event["status"],
            "calibration_date": event["calibration_date"],
            "due_date": event["due_date"],
            "result": event["result"]
        }

        cursor.execute(
            """
            UPDATE calibration_event
            SET calibration_date = %s,
                due_date = %s,
                result = %s,
                measured_value = %s,
                performed_by = %s,
                status = 'COMPLETED'
            WHERE calibration_id = %s
            """,
            (
                calibration_date,
                due_date,
                result,
                measured_value,
                performed_by.strip(),
                calibration_id
            )
        )

        new_values = {
            "calibration_id": calibration_id,
            "calibration_date": calibration_date,
            "due_date": due_date,
            "result": result,
            "measured_value": measured_value,
            "performed_by": performed_by.strip(),
            "status": "COMPLETED"
        }

        write_audit(
            cursor,
            "calibration_event",
            calibration_id,
            "STATUS_CHANGE",
            old_values,
            new_values,
            changed_by
        )

        connection.commit()
        return get_calibration_event(connection, calibration_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def cancel_calibration(connection, calibration_id, data=None):
    data = data or {}
    changed_by = data.get("changed_by", "SYSTEM_USER")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT *
            FROM calibration_event
            WHERE calibration_id = %s
            FOR UPDATE
            """,
            (calibration_id,)
        )
        event = cursor.fetchone()

        if not event:
            raise ValueError("Calibration event does not exist.")

        if event["status"] != "SCHEDULED":
            raise ValueError(
                "Only scheduled calibration events can be cancelled."
            )

        old_values = {
            "status": event["status"],
            "scheduled_date": event["scheduled_date"]
        }

        cursor.execute(
            """
            UPDATE calibration_event
            SET status = 'CANCELLED'
            WHERE calibration_id = %s
            """,
            (calibration_id,)
        )

        new_values = {
            "status": "CANCELLED",
            "reason": data.get("reason")
        }

        write_audit(
            cursor,
            "calibration_event",
            calibration_id,
            "STATUS_CHANGE",
            old_values,
            new_values,
            changed_by
        )

        connection.commit()
        return get_calibration_event(connection, calibration_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

# ============================================================
# CERTIFICATE MANAGEMENT
# ============================================================

def list_certificates(
    connection,
    search=None,
    status=None,
    limit=100,
    offset=0
):
    valid_statuses = {"VALID", "EXPIRED", "REVOKED"}

    if status and status not in valid_statuses:
        raise ValueError("Invalid certificate status.")

    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            term = f"%{search}%"
            conditions.append(
                """
                (
                    c.certificate_id LIKE %s
                    OR c.certificate_number LIKE %s
                    OR c.calibration_id LIKE %s
                    OR c.asset_id LIKE %s
                    OR a.asset_name LIKE %s
                )
                """
            )
            params.extend([term] * 5)

        if status:
            conditions.append("c.status = %s")
            params.append(status)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                c.certificate_id,
                c.certificate_number,
                c.calibration_id,
                c.asset_id,
                a.asset_name,
                c.issue_date,
                c.expiry_date,
                c.file_reference,
                c.status,
                c.created_at
            FROM certificate c
            JOIN asset a ON a.asset_id = c.asset_id
            {where_clause}
            ORDER BY c.created_at DESC, c.certificate_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )
        certificates = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM certificate c
            JOIN asset a ON a.asset_id = c.asset_id
            {where_clause}
            """,
            tuple(params)
        )
        total = cursor.fetchone()["total"]

        return {
            "total": total,
            "certificates": certificates
        }

    finally:
        cursor.close()


def get_certificate(connection, certificate_id):
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                c.certificate_id,
                c.certificate_number,
                c.calibration_id,
                c.asset_id,
                a.asset_name,
                c.issue_date,
                c.expiry_date,
                c.file_reference,
                c.status,
                c.created_at
            FROM certificate c
            JOIN asset a ON a.asset_id = c.asset_id
            WHERE c.certificate_id = %s
            """,
            (certificate_id,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()


def generate_certificate(connection, calibration_id, data=None):
    data = data or {}

    changed_by = data.get("changed_by", "SYSTEM_USER")
    file_reference = data.get("file_reference")

    if file_reference is not None:
        if not isinstance(file_reference, str):
            raise ValueError("file_reference must be text.")

        if len(file_reference) > 255:
            raise ValueError("file_reference cannot exceed 255 characters.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        # Lock the event to prevent duplicate certificate generation.
        cursor.execute(
            """
            SELECT
                calibration_id,
                asset_id,
                calibration_date,
                due_date,
                result,
                status
            FROM calibration_event
            WHERE calibration_id = %s
            FOR UPDATE
            """,
            (calibration_id,)
        )

        event = cursor.fetchone()

        if not event:
            raise ValueError("Calibration event does not exist.")

        if event["status"] != "COMPLETED":
            raise ValueError(
                "Certificate can only be generated for completed calibration."
            )

        if event["result"] != "PASS":
            raise ValueError(
                "Certificate can only be generated for PASS calibration."
            )

        if not event["calibration_date"] or not event["due_date"]:
            raise ValueError(
                "Calibration date and due date are required."
            )

        cursor.execute(
            """
            SELECT certificate_id
            FROM certificate
            WHERE calibration_id = %s
            FOR UPDATE
            """,
            (calibration_id,)
        )

        if cursor.fetchone():
            raise ValueError(
                "A certificate already exists for this calibration."
            )

        certificate_id = f"CERT-{calibration_id}"
        certificate_number = f"CERTNO-{calibration_id}"

        cursor.execute(
            """
            INSERT INTO certificate (
                certificate_id,
                calibration_id,
                asset_id,
                certificate_number,
                issue_date,
                expiry_date,
                file_reference,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'VALID')
            """,
            (
                certificate_id,
                calibration_id,
                event["asset_id"],
                certificate_number,
                event["calibration_date"],
                event["due_date"],
                file_reference
            )
        )

        new_values = {
            "certificate_id": certificate_id,
            "certificate_number": certificate_number,
            "calibration_id": calibration_id,
            "asset_id": event["asset_id"],
            "issue_date": event["calibration_date"],
            "expiry_date": event["due_date"],
            "status": "VALID"
        }

        write_audit(
            cursor,
            "certificate",
            certificate_id,
            "INSERT",
            None,
            new_values,
            changed_by
        )

        connection.commit()

        return get_certificate(connection, certificate_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
