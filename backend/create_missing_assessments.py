
import argparse

from backend.db import get_db_connection
from backend.services.impact_assessment_service import create_assessment


def get_missing_assessments():
    connection = get_db_connection()

    if connection is None:
        raise RuntimeError("Database connection failed")

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                ce.calibration_id,
                ce.asset_id,
                wo.work_order_id
            FROM calibration_event ce
            JOIN work_order wo
                ON wo.calibration_id = ce.calibration_id
                AND wo.asset_id = ce.asset_id
                AND wo.work_type = 'CORRECTIVE_ACTION'
            LEFT JOIN impact_assessment ia
                ON ia.calibration_id = ce.calibration_id
            WHERE ce.result = 'FAIL'
              AND ia.assessment_id IS NULL
            ORDER BY ce.calibration_id
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create missing draft impact assessments."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the draft assessments."
    )
    args = parser.parse_args()

    records = get_missing_assessments()

    print("Missing assessments found:", len(records))

    for record in records[:5]:
        print(
            record["calibration_id"],
            record["asset_id"],
            record["work_order_id"]
        )

    if not args.apply:
        print("\nDRY RUN ONLY. No database records were changed.")
        print("Review the output before running with --apply.")
        return

    created = 0
    failed = 0

    for record in records:
        try:
            result = create_assessment(
                {
                    "calibration_id": record["calibration_id"],
                    "asset_id": record["asset_id"],
                    "work_order_id": record["work_order_id"],
                    "notes": (
                        "Pending quality engineer impact assessment. "
                        "No impact decision has been recorded."
                    )
                },
                changed_by="Assessment preparation"
            )

            created += 1
            print("CREATED:", result["assessment_id"])

        except Exception as error:
            failed += 1
            print(
                "FAILED:",
                record["calibration_id"],
                str(error)
            )

    print("\nBatch processing finished.")
    print("Created:", created)
    print("Failed:", failed)


if __name__ == "__main__":
    main()
