
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "generated"
OUTPUT_FILE = DATA_DIR / "seed_data.sql"

BATCH_SIZE = 500

TABLES = {
    "instrument_type": [
        "instrument_type_id", "type_name", "description", "created_at"
    ],
    "supplier": [
        "supplier_id", "supplier_name", "contact_person", "email",
        "phone", "created_at"
    ],
    "asset": [
        "asset_id", "instrument_type_id", "asset_name", "location",
        "status", "created_at"
    ],
    "calibration_plan": [
        "plan_id", "asset_id", "interval_days", "effective_from",
        "effective_to", "status", "created_at"
    ],
    "calibration_event": [
        "calibration_id", "asset_id", "plan_id", "supplier_id",
        "calibration_date", "due_date", "result", "measured_value",
        "performed_by", "status", "created_at"
    ],
    "certificate": [
        "certificate_id", "calibration_id", "asset_id",
        "certificate_number", "issue_date", "expiry_date",
        "file_reference", "status", "created_at"
    ],
    "work_order": [
        "work_order_id", "asset_id", "calibration_id", "work_type",
        "start_date", "end_date", "downtime_minutes", "status",
        "description", "created_at"
    ],
    "production_use": [
        "use_id", "asset_id", "use_start", "use_end",
        "production_line", "exception_reference", "created_at"
    ],
    "alert": [
        "alert_id", "asset_id", "calibration_id", "use_id",
        "alert_type", "severity", "message", "status",
        "created_at", "resolved_at"
    ],
    "audit_record": [
        "audit_id", "entity_name", "entity_id", "action",
        "old_values", "new_values", "changed_at", "changed_by"
    ],
}


def sql_value(value):
    if value is None or value == "":
        return "NULL"

    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "''")
    value = value.replace("\x00", "\\0")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")

    return "'" + value + "'"


def export_table(output, table_name, columns):
    csv_path = DATA_DIR / f"{table_name}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    column_names = ", ".join(f"`{column}`" for column in columns)

    insert_prefix = (
        f"INSERT INTO `{table_name}` ({column_names}) VALUES\n"
    )

    total = 0
    batch = []

    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        missing = [
            column for column in columns
            if column not in (reader.fieldnames or [])
        ]

        if missing:
            raise ValueError(
                f"{table_name}.csv missing columns: {missing}"
            )

        for row in reader:
            values = ", ".join(
                sql_value(row[column]) for column in columns
            )
            batch.append(f"({values})")

            if len(batch) >= BATCH_SIZE:
                output.write(insert_prefix)
                output.write(",\n".join(batch))
                output.write(";\n\n")

                total += len(batch)
                batch.clear()

        if batch:
            output.write(insert_prefix)
            output.write(",\n".join(batch))
            output.write(";\n\n")
            total += len(batch)

    print(f"Exported {total:,} rows: {table_name}")
    return total


def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Generated data directory not found: {DATA_DIR}"
        )

    total_rows = 0

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="\n") as output:
        output.write("-- Calibration Management and Production Compliance System\n")
        output.write("-- Generated from baseline CSV datasets\n")
        output.write("-- Random seed: 20261022\n\n")
        output.write("SET NAMES utf8mb4;\n")
        output.write("START TRANSACTION;\n\n")

        for table_name, columns in TABLES.items():
            total_rows += export_table(
                output, table_name, columns
            )

        output.write("COMMIT;\n")

    print("\nSQL export completed successfully.")
    print(f"Total exported rows: {total_rows:,}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
