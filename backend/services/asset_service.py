
import json
import re


VALID_STATUSES = {"ACTIVE", "INACTIVE"}


def _get_asset(cursor, asset_id):
    cursor.execute(
        """
        SELECT
            a.asset_id,
            a.instrument_type_id,
            it.type_name,
            a.asset_name,
            a.location,
            a.status,
            a.created_at
        FROM asset a
        JOIN instrument_type it
          ON it.instrument_type_id = a.instrument_type_id
        WHERE a.asset_id = %s
        """,
        (asset_id,)
    )
    return cursor.fetchone()


def _write_audit(
    cursor, entity_id, action, old_values, new_values, changed_by
):
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
        VALUES ('asset', %s, %s, %s, %s, %s)
        """,
        (
            entity_id,
            action,
            json.dumps(old_values, default=str) if old_values else None,
            json.dumps(new_values, default=str) if new_values else None,
            changed_by
        )
    )


def list_assets(connection, search=None, status=None,
                instrument_type_id=None, limit=100, offset=0):
    cursor = connection.cursor(dictionary=True)

    try:
        conditions = []
        params = []

        if search:
            conditions.append(
                "(a.asset_id LIKE %s OR a.asset_name LIKE %s "
                "OR a.location LIKE %s)"
            )
            term = f"%{search}%"
            params.extend([term, term, term])

        if status:
            conditions.append("a.status = %s")
            params.append(status)

        if instrument_type_id is not None:
            conditions.append("a.instrument_type_id = %s")
            params.append(instrument_type_id)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor.execute(
            f"""
            SELECT
                a.asset_id,
                a.instrument_type_id,
                it.type_name,
                a.asset_name,
                a.location,
                a.status,
                a.created_at
            FROM asset a
            JOIN instrument_type it
              ON it.instrument_type_id = a.instrument_type_id
            {where_clause}
            ORDER BY a.asset_id
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        records = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM asset a
            {where_clause}
            """,
            tuple(params)
        )

        total = cursor.fetchone()["total"]

        return {"total": total, "assets": records}

    finally:
        cursor.close()


def get_asset(connection, asset_id):
    cursor = connection.cursor(dictionary=True)

    try:
        return _get_asset(cursor, asset_id)
    finally:
        cursor.close()


def get_instrument_types(connection):
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT instrument_type_id, type_name, description
            FROM instrument_type
            ORDER BY type_name
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def create_asset(connection, data):
    instrument_type_id = data.get("instrument_type_id")
    asset_name = data.get("asset_name")
    location = data.get("location")
    status = data.get("status", "ACTIVE")
    changed_by = data.get("changed_by", "SYSTEM_USER")

    if not isinstance(asset_name, str) or not asset_name.strip():
        raise ValueError("asset_name is required.")

    if not isinstance(instrument_type_id, int):
        raise ValueError("instrument_type_id must be an integer.")

    if status not in VALID_STATUSES:
        raise ValueError("Status must be ACTIVE or INACTIVE.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        # Generate the next asset ID.
        cursor.execute(
            """
            SELECT asset_id
            FROM asset
            ORDER BY asset_id DESC
            LIMIT 1
            FOR UPDATE
            """
        )

        last_asset = cursor.fetchone()
        last_number = (
            int(last_asset["asset_id"].split("-")[1])
            if last_asset else 0
        )

        asset_id = f"AST-{last_number + 1:06d}"

        cursor.execute(
            """
            INSERT INTO asset (
                asset_id,
                instrument_type_id,
                asset_name,
                location,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                asset_id,
                instrument_type_id,
                asset_name.strip(),
                location.strip() if isinstance(location, str) and location.strip() else None,
                status
            )
        )

        new_values = {
            "asset_id": asset_id,
            "instrument_type_id": instrument_type_id,
            "asset_name": asset_name.strip(),
            "location": location,
            "status": status
        }

        _write_audit(
            cursor,
            asset_id,
            "INSERT",
            None,
            new_values,
            changed_by
        )

        connection.commit()

        return _get_asset(cursor, asset_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def update_asset(connection, asset_id, data):
    changed_by = data.get("changed_by", "SYSTEM_USER")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        old_values = _get_asset(cursor, asset_id)

        if old_values is None:
            raise LookupError("Asset not found.")

        instrument_type_id = data.get(
            "instrument_type_id",
            old_values["instrument_type_id"]
        )
        asset_name = data.get("asset_name", old_values["asset_name"])
        location = data.get("location", old_values["location"])

        if not isinstance(asset_name, str) or not asset_name.strip():
            raise ValueError("asset_name is required.")

        if not isinstance(instrument_type_id, int):
            raise ValueError("instrument_type_id must be an integer.")

        cursor.execute(
            """
            UPDATE asset
            SET instrument_type_id = %s,
                asset_name = %s,
                location = %s
            WHERE asset_id = %s
            """,
            (
                instrument_type_id,
                asset_name.strip(),
                location.strip() if isinstance(location, str) and location.strip() else None,
                asset_id
            )
        )

        new_values = {
            "asset_id": asset_id,
            "instrument_type_id": instrument_type_id,
            "asset_name": asset_name.strip(),
            "location": location,
            "status": old_values["status"]
        }

        _write_audit(
            cursor,
            asset_id,
            "UPDATE",
            old_values,
            new_values,
            changed_by
        )

        connection.commit()

        return _get_asset(cursor, asset_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def change_asset_status(connection, asset_id, status, changed_by):
    if status not in VALID_STATUSES:
        raise ValueError("Status must be ACTIVE or INACTIVE.")

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        old_values = _get_asset(cursor, asset_id)

        if old_values is None:
            raise LookupError("Asset not found.")

        if old_values["status"] == status:
            connection.commit()
            return old_values

        cursor.execute(
            "UPDATE asset SET status = %s WHERE asset_id = %s",
            (status, asset_id)
        )

        new_values = dict(old_values)
        new_values["status"] = status

        _write_audit(
            cursor,
            asset_id,
            "STATUS_CHANGE",
            old_values,
            new_values,
            changed_by
        )

        connection.commit()

        return _get_asset(cursor, asset_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
