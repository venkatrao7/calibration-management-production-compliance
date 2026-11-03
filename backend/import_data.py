"""
Import generated CSV datasets into the MySQL database.
Run from the project root:
    python backend/import_data.py

The script checks that all target tables are empty before importing,
then loads parent tables before dependent tables in batches.
"""
import csv
from pathlib import Path

from db import get_db_connection

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "generated"
BATCH_SIZE = 1000

# Column order must match the generated CSV headers and database schema.
IMPORT_ORDER = [
    ("instrument_type", [
        "instrument_type_id", "type_name", "description", "created_at"
    ]),
    ("supplier", [
        "supplier_id", "supplier_name", "contact_person", "email",
        "phone", "created_at"
    ]),
    ("asset", [
        "asset_id", "instrument_type_id", "asset_name", "location",
        "status", "created_at"
    ]),
    ("calibration_plan", [
        "plan_id", "asset_id", "interval_days", "effective_from",
        "effective_to", "status", "created_at"
    ]),
    ("calibration_event", [
        "calibration_id", "asset_id", "plan_id", "supplier_id",
        "calibration_date", "due_date", "result", "measured_value",
        "performed_by", "status", "created_at"
    ]),
    ("certificate", [
        "certificate_id", "calibration_id", "asset_id",
        "certificate_number", "issue_date", "expiry_date",
        "file_reference", "status", "created_at"
    ]),
    ("work_order", [
        "work_order_id", "asset_id", "calibration_id", "work_type",
        "start_date", "end_date", "downtime_minutes", "status",
        "description", "created_at"
    ]),
    ("production_use", [
        "use_id", "asset_id", "use_start", "use_end",
        "production_line", "exception_reference", "created_at"
    ]),
    ("alert", [
        "alert_id", "asset_id", "calibration_id", "use_id",
        "alert_type", "severity", "message", "status",
        "created_at", "resolved_at"
    ]),
    ("audit_record", [
        "audit_id", "entity_name", "entity_id", "action",
        "old_values", "new_values", "changed_at", "changed_by"
    ]),
]


def clean_value(value):
    # Empty CSV cells represent SQL NULL for optional fields.
    if value == "":
        return None
    return value


def load_csv_rows(csv_path, columns):
    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        missing = [column for column in columns if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{csv_path.name} is missing required columns: {missing}"
            )
        for row in reader:
            yield tuple(clean_value(row[column]) for column in columns)


def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Generated data folder not found: {DATA_DIR}\n"
            "Run: python backend/generate_data.py"
        )

    connection = get_db_connection()
    if connection is None:
        raise RuntimeError(
            "Could not connect to MySQL. Check the local settings in backend/db.py."
        )

    cursor = connection.cursor()
    try:
        # Protect against duplicate imports or mixing old and new generated data.
        nonempty = []
        for table_name, _ in IMPORT_ORDER:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            if count:
                nonempty.append(f"{table_name}: {count} rows")

        if nonempty:
            raise RuntimeError(
                "Import stopped because these tables are not empty:\n"
                + "\n".join(nonempty)
                + "\nDo not delete data automatically. Review the database first."
            )

        for table_name, columns in IMPORT_ORDER:
            csv_path = DATA_DIR / f"{table_name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing generated file: {csv_path}")

            column_sql = ", ".join(f"`{column}`" for column in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = (
                f"INSERT INTO `{table_name}` ({column_sql}) "
                f"VALUES ({placeholders})"
            )

            total = 0
            batch = []
            for values in load_csv_rows(csv_path, columns):
                batch.append(values)
                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(insert_sql, batch)
                    total += len(batch)
                    batch.clear()

            if batch:
                cursor.executemany(insert_sql, batch)
                total += len(batch)

            connection.commit()
            print(f"Imported {total:,} rows into {table_name}")

        print("\nAll 10 datasets imported successfully.")

    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
