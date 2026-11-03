"""
Business-rule queries for calibration and production compliance.

These functions read existing MySQL records and return findings.
They do not modify or delete source records.
"""
from datetime import date, timedelta


def _fetch_all(connection, query, params=()):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()


def calculate_due_date(connection, asset_id, calibration_date):
    """
    Return the due date from the plan effective on calibration_date.
    Raises ValueError if no applicable plan exists.
    """
    query = """
        SELECT DATE_ADD(%s, INTERVAL interval_days DAY) AS due_date
        FROM calibration_plan
        WHERE asset_id = %s
          AND status = 'ACTIVE'
          AND effective_from <= %s
          AND (effective_to IS NULL OR effective_to >= %s)
        ORDER BY effective_from DESC, plan_id DESC
        LIMIT 1
    """
    rows = _fetch_all(
        connection,
        query,
        (calibration_date, asset_id, calibration_date, calibration_date)
    )
    if not rows:
        raise ValueError(
            f"No active calibration plan for asset {asset_id} "
            f"on {calibration_date}"
        )
    return rows[0]["due_date"]


def get_due_date_inconsistencies(connection):
    """
    Find calibration events whose stored due dates do not match
    the due date derived from the applicable calibration plan.
    """
    query = """
        SELECT
            ce.calibration_id,
            ce.asset_id,
            ce.plan_id AS recorded_plan_id,
            cp.plan_id AS expected_plan_id,
            ce.calibration_date,
            ce.due_date AS stored_due_date,
            DATE_ADD(
                ce.calibration_date,
                INTERVAL cp.interval_days DAY
            ) AS expected_due_date,
            cp.interval_days,
            CASE
                WHEN cp.plan_id IS NULL THEN 'NO_EFFECTIVE_PLAN'
                WHEN ce.plan_id <> cp.plan_id THEN 'PLAN_REFERENCE_MISMATCH'
                ELSE 'DUE_DATE_MISMATCH'
            END AS issue_type
        FROM calibration_event ce
        LEFT JOIN calibration_plan cp
          ON cp.plan_id = (
              SELECT cp2.plan_id
              FROM calibration_plan cp2
              WHERE cp2.asset_id = ce.asset_id
                AND cp2.status = 'ACTIVE'
                AND cp2.effective_from <= ce.calibration_date
                AND (
                    cp2.effective_to IS NULL
                    OR cp2.effective_to >= ce.calibration_date
                )
              ORDER BY cp2.effective_from DESC, cp2.plan_id DESC
              LIMIT 1
          )
        WHERE cp.plan_id IS NULL
           OR ce.plan_id <> cp.plan_id
           OR ce.due_date <> DATE_ADD(
               ce.calibration_date,
               INTERVAL cp.interval_days DAY
           )
        ORDER BY ce.calibration_date, ce.calibration_id
    """
    return _fetch_all(connection, query)

def get_overdue_assets(connection, as_of_date=None):
    """
    Return assets with no completed calibration, a latest failed calibration,
    or a latest calibration whose due date is before as_of_date.
    """
    if as_of_date is None:
        as_of_date = date.today()

    query = """
        WITH ranked_calibrations AS (
            SELECT
                calibration_id,
                asset_id,
                calibration_date,
                due_date,
                result,
                ROW_NUMBER() OVER (
                    PARTITION BY asset_id
                    ORDER BY calibration_date DESC, calibration_id DESC
                ) AS row_num
            FROM calibration_event
            WHERE status = 'COMPLETED'
              AND calibration_date <= %s
        )
        SELECT
            a.asset_id,
            a.asset_name,
            rc.calibration_id,
            rc.calibration_date,
            rc.due_date,
            rc.result,
            CASE
                WHEN rc.calibration_id IS NULL THEN 'NEVER_CALIBRATED'
                WHEN rc.result = 'FAIL' THEN 'LATEST_CALIBRATION_FAILED'
                WHEN rc.due_date < %s THEN 'CALIBRATION_OVERDUE'
            END AS issue_type
        FROM asset a
        LEFT JOIN ranked_calibrations rc
          ON rc.asset_id = a.asset_id AND rc.row_num = 1
        WHERE rc.calibration_id IS NULL
           OR rc.result = 'FAIL'
           OR rc.due_date < %s
        ORDER BY a.asset_id
    """
    return _fetch_all(connection, query, (as_of_date, as_of_date, as_of_date))



def get_production_use_violations(connection, start_date=None, end_date=None):
    """
    Return production-use records without a valid passing calibration window.

    An emergency extension is accepted only when:
    - Its status is APPROVED.
    - It belongs to the same asset.
    - Its validity covers the production-use period.
    - Its approval details are present.
    - Its calibration_id is either NULL or matches the latest calibration.

    Extensions do not override missing or failed calibrations.
    """
    conditions = []
    params = []

    if start_date is not None:
        conditions.append("DATE(p.use_start) >= %s")
        params.append(start_date)

    if end_date is not None:
        conditions.append("DATE(p.use_start) <= %s")
        params.append(end_date)

    date_filter = ""
    if conditions:
        date_filter = " AND " + " AND ".join(conditions)

    query = f"""
        SELECT
            p.use_id,
            p.asset_id,
            p.use_start,
            p.use_end,
            p.exception_reference,
            ce.calibration_id,
            ce.due_date,
            ce.result,
            CASE
                WHEN ce.calibration_id IS NULL
                    THEN 'NO_PRIOR_CALIBRATION'
                WHEN ce.result <> 'PASS'
                    THEN 'LATEST_CALIBRATION_FAILED'
                WHEN DATE(p.use_start) > ce.due_date
                    THEN 'CALIBRATION_EXPIRED'
            END AS issue_type

        FROM production_use p

        LEFT JOIN calibration_event ce
          ON ce.calibration_id = (
              SELECT ce2.calibration_id
              FROM calibration_event ce2
              WHERE ce2.asset_id = p.asset_id
                AND ce2.status = 'COMPLETED'
                AND ce2.calibration_date <= DATE(p.use_start)
              ORDER BY
                ce2.calibration_date DESC,
                ce2.calibration_id DESC
              LIMIT 1
          )

        LEFT JOIN emergency_extension ee
          ON ee.extension_reference = p.exception_reference

        WHERE (
            ce.calibration_id IS NULL
            OR ce.result <> 'PASS'
            OR DATE(p.use_start) > ce.due_date
        )

        AND NOT (
            ce.calibration_id IS NOT NULL
            AND ce.result = 'PASS'
            AND DATE(p.use_start) > ce.due_date

            AND ee.extension_reference IS NOT NULL
            AND ee.status = 'APPROVED'
            AND ee.asset_id = p.asset_id

            AND (
                ee.calibration_id IS NULL
                OR ee.calibration_id = ce.calibration_id
            )

            AND ee.approved_by IS NOT NULL
            AND ee.approved_at IS NOT NULL

            AND p.use_start >= ee.valid_from
            AND COALESCE(p.use_end, p.use_start) <= ee.valid_to
        )

        {date_filter}

        ORDER BY p.use_start, p.use_id
    """

    return _fetch_all(connection, query, tuple(params))


def get_certificate_gaps(connection):
    """Return completed PASS calibration events that have no certificate."""
    query = """
        SELECT
            ce.calibration_id,
            ce.asset_id,
            ce.calibration_date,
            ce.due_date,
            ce.result
        FROM calibration_event ce
        LEFT JOIN certificate c
          ON c.calibration_id = ce.calibration_id
         AND c.asset_id = ce.asset_id
        WHERE ce.status = 'COMPLETED'
          AND ce.result = 'PASS'
          AND c.certificate_id IS NULL
        ORDER BY ce.calibration_date, ce.calibration_id
    """
    return _fetch_all(connection, query)

def get_certificate_asset_mismatches(connection):
    """Find certificates whose asset does not match their calibration event."""
    query = """
        SELECT
            c.certificate_id,
            c.calibration_id,
            c.asset_id AS certificate_asset_id,
            ce.asset_id AS calibration_asset_id,
            'CERTIFICATE_ASSET_MISMATCH' AS issue_type
        FROM certificate c
        INNER JOIN calibration_event ce
            ON ce.calibration_id = c.calibration_id
        WHERE c.asset_id <> ce.asset_id
        ORDER BY c.certificate_id
    """
    return _fetch_all(connection, query)

def get_failed_calibrations_without_corrective_action(connection):
    """
    Return failed completed calibrations that are missing:
    1. A non-cancelled corrective work order.
    2. A completed impact assessment.

    Each missing requirement is reported separately.
    """
    query = """
        SELECT
            ce.calibration_id,
            ce.asset_id,
            ce.calibration_date,
            ce.result,
            'MISSING_CORRECTIVE_WORK_ORDER' AS issue_type
        FROM calibration_event ce
        WHERE ce.status = 'COMPLETED'
          AND ce.result = 'FAIL'
          AND NOT EXISTS (
              SELECT 1
              FROM work_order wo
              WHERE wo.calibration_id = ce.calibration_id
                AND wo.asset_id = ce.asset_id
                AND wo.work_type = 'CORRECTIVE_ACTION'
                AND wo.status <> 'CANCELLED'
          )

        UNION ALL

        SELECT
            ce.calibration_id,
            ce.asset_id,
            ce.calibration_date,
            ce.result,
            'MISSING_COMPLETED_IMPACT_ASSESSMENT' AS issue_type
        FROM calibration_event ce
        WHERE ce.status = 'COMPLETED'
          AND ce.result = 'FAIL'
          AND NOT EXISTS (
              SELECT 1
              FROM impact_assessment ia
              WHERE ia.calibration_id = ce.calibration_id
                AND ia.asset_id = ce.asset_id
                AND ia.assessment_status = 'COMPLETED'
          )

        ORDER BY calibration_date, calibration_id
    """

    return _fetch_all(connection, query)



def run_compliance_checks(connection, as_of_date=None):
    """
    Run all read-only compliance checks and return their findings.
    No source data or alerts are modified by this function.
    """
    if as_of_date is None:
        as_of_date = date.today()

    failed_calibration_findings = (
        get_failed_calibrations_without_corrective_action(connection)
    )

    missing_corrective_work_orders = [
        item for item in failed_calibration_findings
        if item["issue_type"] == "MISSING_CORRECTIVE_WORK_ORDER"
    ]

    missing_impact_assessments = [
        item for item in failed_calibration_findings
        if item["issue_type"] == "MISSING_COMPLETED_IMPACT_ASSESSMENT"
    ]

    return {
        "as_of_date": str(as_of_date),

        "overdue_assets":
            get_overdue_assets(connection, as_of_date),

        "due_date_inconsistencies":
            get_due_date_inconsistencies(connection),

        "production_use_violations":
            get_production_use_violations(connection),

        "certificate_gaps":
            get_certificate_gaps(connection),
        "certificate_asset_mismatches":
            get_certificate_asset_mismatches(connection),

        "failed_calibrations_without_corrective_action":
            missing_corrective_work_orders,

        "failed_calibrations_without_impact_assessment":
            missing_impact_assessments
    }
