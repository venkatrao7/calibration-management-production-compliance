
from backend.db import get_db_connection
from backend.services.compliance_service import (
    get_failed_calibrations_without_corrective_action
)

connection = get_db_connection()

if connection is None:
    raise RuntimeError("Database connection failed")

cursor = connection.cursor()

calibration_id = "CAL-AST-000001-2026-000001"
asset_id = "AST-000001"
work_order_id = "WO-2026-000001"
assessment_id = "TEST-IMPACT-001"


def check_assessment():
    findings = get_failed_calibrations_without_corrective_action(
        connection
    )

    return [
        item for item in findings
        if item["calibration_id"] == calibration_id
        and item["issue_type"] == "MISSING_COMPLETED_IMPACT_ASSESSMENT"
    ]


try:
    # Test 1: No assessment exists.
    initial = check_assessment()
    print("No assessment detected:", len(initial) == 1)

    # Test 2: Create a DRAFT assessment.
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
            "Controlled impact assessment test"
        )
    )

    draft = check_assessment()
    print("DRAFT assessment flagged:", len(draft) == 1)

    # Test 3: Complete the assessment.
    cursor.execute(
        """
        UPDATE impact_assessment
        SET assessment_status = 'COMPLETED',
            impact_category = 'NO_IMPACT',
            disposition = 'No affected production identified during test.',
            assessed_by = 'TEST_ASSESSOR',
            assessed_at = '2026-11-02 12:00:00'
        WHERE assessment_id = %s
        """,
        (assessment_id,)
    )

    completed = check_assessment()
    print("COMPLETED assessment accepted:", len(completed) == 0)

    print(
        "All three checks passed:",
        len(initial) == 1
        and len(draft) == 1
        and len(completed) == 0
    )

finally:
    connection.rollback()
    cursor.close()
    connection.close()
    print("Test transaction rolled back.")
