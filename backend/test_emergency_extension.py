
from backend.db import get_db_connection
from backend.services.compliance_service import get_production_use_violations

connection = get_db_connection()

if connection is None:
    raise RuntimeError("Database connection failed")

test_use_id = "TEST-USE-EMERGENCY-001"
test_extension_id = "TEST-EXT-EMERGENCY-001"

try:
    cursor = connection.cursor()

    # 1. Create a pending emergency extension.
    cursor.execute(
        """
        INSERT INTO emergency_extension (
            extension_reference, asset_id, calibration_id,
            valid_from, valid_to, reason, status, requested_by
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, 'PENDING', %s
        )
        """,
        (
            test_extension_id,
            "AST-000002",
            "CAL-AST-000002-2026-004002",
            "2026-11-02 09:00:00",
            "2026-11-02 18:00:00",
            "Controlled emergency extension test",
            "TEST_USER",
        ),
    )

    # 2. Create a production-use record using that extension.
    cursor.execute(
        """
        INSERT INTO production_use (
            use_id, asset_id, use_start, use_end,
            production_line, exception_reference
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            test_use_id,
            "AST-000002",
            "2026-11-02 10:00:00",
            "2026-11-02 10:30:00",
            "TEST_LINE",
            test_extension_id,
        ),
    )

    def check_test_record():
        violations = get_production_use_violations(
            connection,
            start_date="2026-11-02",
            end_date="2026-11-02",
        )
        return [
            item for item in violations
            if item["use_id"] == test_use_id
        ]

    # 3. Pending extension must be flagged.
    pending = check_test_record()
    print("PENDING extension flagged:", len(pending) == 1)

    # 4. Approve the extension.
    cursor.execute(
        """
        UPDATE emergency_extension
        SET status = 'APPROVED',
            approved_by = 'TEST_APPROVER',
            approved_at = '2026-11-02 09:00:00'
        WHERE extension_reference = %s
        """,
        (test_extension_id,),
    )

    approved = check_test_record()
    print("APPROVED extension accepted:", len(approved) == 0)

    # 5. Revoke the extension.
    cursor.execute(
        """
        UPDATE emergency_extension
        SET status = 'REVOKED'
        WHERE extension_reference = %s
        """,
        (test_extension_id,),
    )

    revoked = check_test_record()
    print("REVOKED extension flagged:", len(revoked) == 1)

    print("All three checks passed:",
          len(pending) == 1
          and len(approved) == 0
          and len(revoked) == 1)

finally:
    # Remove all temporary test changes.
    connection.rollback()
    connection.close()
    print("Test transaction rolled back.")
