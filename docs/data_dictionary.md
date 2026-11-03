
# Calibration Management and Production Compliance System
# Data Dictionary

## 1. instrument_type

Purpose: Stores the types of measuring instruments.

| Field | Data type | Required | Description |
|---|---|---|---|
| instrument_type_id | INT | Yes | Primary key, auto increment |
| type_name | VARCHAR(100) | Yes | Unique instrument type name |
| description | TEXT | No | Instrument type description |
| created_at | TIMESTAMP | No | Record creation time |

## 2. asset

Purpose: Stores instrument and asset master records.

| Field | Data type | Required | Description |
|---|---|---|---|
| asset_id | VARCHAR(20) | Yes | Primary key; format AST-000001 |
| instrument_type_id | INT | Yes | FK to instrument_type |
| asset_name | VARCHAR(100) | Yes | Asset name |
| location | VARCHAR(100) | No | Asset location |
| status | VARCHAR(30) | Yes | Asset lifecycle status |
| created_at | TIMESTAMP | No | Record creation time |

## 3. supplier

Purpose: Stores calibration service supplier information.

| Field | Data type | Required | Description |
|---|---|---|---|
| supplier_id | INT | Yes | Primary key, auto increment |
| supplier_name | VARCHAR(150) | Yes | Supplier name |
| contact_person | VARCHAR(100) | No | Contact person |
| email | VARCHAR(150) | No | Supplier email |
| phone | VARCHAR(20) | No | Supplier phone |
| created_at | TIMESTAMP | No | Record creation time |

## 4. calibration_plan

Purpose: Defines calibration intervals for assets.

| Field | Data type | Required | Description |
|---|---|---|---|
| plan_id | INT | Yes | Primary key, auto increment |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| interval_days | INT | Yes | Calibration interval in days |
| effective_from | DATE | Yes | Plan start date |
| effective_to | DATE | No | Plan end date |
| status | ENUM | No | ACTIVE or INACTIVE |
| created_at | TIMESTAMP | No | Record creation time |

Validation:
- interval_days must be greater than zero.
- effective_to must not precede effective_from.
- Due dates are derived from calibration dates and applicable plan intervals.

## 5. calibration_event

Purpose: Records calibration activities and results.

| Field | Data type | Required | Description |
|---|---|---|---|
| calibration_id | VARCHAR(60) | Yes | Primary key; CAL-asset-id-2026-000001 format |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| plan_id | INT | No | FK to calibration_plan |
| supplier_id | INT | No | FK to supplier |
| calibration_date | DATE | Yes | Calibration date |
| due_date | DATE | Yes | Next calibration due date |
| result | ENUM | Yes | PASS or FAIL |
| measured_value | DECIMAL(12,4) | No | Measured calibration value |
| performed_by | VARCHAR(100) | No | Person performing calibration |
| status | ENUM | No | COMPLETED or CANCELLED |
| created_at | TIMESTAMP | No | Record creation time |

Validation:
- due_date must not precede calibration_date.
- Due date must agree with the applicable calibration plan.
- Failed calibration requires impact assessment and corrective action.

## 6. certificate

Purpose: Stores certificates associated with calibration events.

| Field | Data type | Required | Description |
|---|---|---|---|
| certificate_id | VARCHAR(80) | Yes | Primary key; CERT-calibration-id format |
| calibration_id | VARCHAR(60) | Yes | FK to calibration_event |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| certificate_number | VARCHAR(100) | Yes | Unique certificate number |
| issue_date | DATE | Yes | Certificate issue date |
| expiry_date | DATE | No | Certificate expiry date |
| file_reference | VARCHAR(255) | No | Certificate file reference |
| status | ENUM | No | VALID, EXPIRED or REVOKED |
| created_at | TIMESTAMP | No | Record creation time |

Validation:
- Certificate asset must match its calibration event asset.
- Expiry date must not precede issue date.
- Missing certificates must be identifiable.

## 7. work_order

Purpose: Records maintenance, downtime and corrective activities.

| Field | Data type | Required | Description |
|---|---|---|---|
| work_order_id | VARCHAR(30) | Yes | Primary key; WO-2026-000001 format |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| calibration_id | VARCHAR(60) | No | FK to calibration_event |
| work_type | VARCHAR(50) | Yes | Work activity type |
| start_date | DATETIME | Yes | Work start time |
| end_date | DATETIME | No | Work completion time |
| downtime_minutes | INT | No | Downtime in minutes |
| status | ENUM | No | OPEN, IN_PROGRESS, COMPLETED or CANCELLED |
| description | TEXT | No | Work description |
| created_at | TIMESTAMP | No | Record creation time |

Validation:
- Downtime cannot be negative.
- End date cannot precede start date.
- Failed calibration must have a linked impact assessment and corrective action record.

## 8. production_use

Purpose: Records production usage of instruments.

| Field | Data type | Required | Description |
|---|---|---|---|
| use_id | VARCHAR(80) | Yes | Primary key; USE-asset-id-timestamp format |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| use_start | DATETIME | Yes | Production use start |
| use_end | DATETIME | No | Production use end |
| production_line | VARCHAR(100) | No | Production line |
| exception_reference | VARCHAR(100) | No | Approved exception reference |
| created_at | TIMESTAMP | No | Record creation time |

Validation:
- Use end cannot precede use start.
- Production usage outside a valid calibration period must be flagged unless a valid exception applies.

## 9. alert

Purpose: Stores alerts generated from compliance checks.

| Field | Data type | Required | Description |
|---|---|---|---|
| alert_id | BIGINT | Yes | Primary key, auto increment |
| asset_id | VARCHAR(20) | Yes | FK to asset |
| calibration_id | VARCHAR(60) | No | FK to calibration_event |
| use_id | VARCHAR(80) | No | FK to production_use |
| alert_type | VARCHAR(60) | Yes | Alert category |
| severity | ENUM | Yes | LOW, MEDIUM, HIGH or CRITICAL |
| message | TEXT | Yes | Alert description |
| status | ENUM | No | OPEN, ACKNOWLEDGED or RESOLVED |
| created_at | TIMESTAMP | No | Alert creation time |
| resolved_at | DATETIME | No | Alert resolution time |

## 10. audit_record

Purpose: Maintains a history of entity changes.

| Field | Data type | Required | Description |
|---|---|---|---|
| audit_id | BIGINT | Yes | Primary key, auto increment |
| entity_name | VARCHAR(100) | Yes | Changed entity |
| entity_id | VARCHAR(100) | Yes | Changed record ID |
| action | ENUM | Yes | INSERT, UPDATE, DELETE or STATUS_CHANGE |
| old_values | JSON | No | Previous record values |
| new_values | JSON | No | New record values |
| changed_at | TIMESTAMP | No | Change timestamp |
| changed_by | VARCHAR(100) | No | Person making the change |

## General data validation rules

1. Primary keys must be unique.
2. Foreign keys must reference existing parent records.
3. Required fields cannot be NULL.
4. Enum values must match the defined options.
5. Dates and timestamps must follow valid chronological order.
6. Calibration due dates must be derived from applicable plans.
7. Certificate and calibration asset references must match.
8. Production usage outside valid calibration periods must be identified.
9. Failed calibration must trigger impact assessment and corrective action.
10. Historical changes must be preserved as records.

## Synthetic dataset configuration

- Random seed: 20261022
- Instruments: 2,000
- Calibration events: 5,000
- Production use events: 100,000
- Period: One year
- Data generation order: Master data first, dependent transactions second.
- Ground-truth anomaly labels: Maintained separately from input features.
