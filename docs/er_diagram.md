
# Entity Relationship Diagram
## Calibration Management and Production Compliance System

The database contains 12 entities. The diagram shows the primary relationships enforced by the database schema.

```mermaid
erDiagram
    INSTRUMENT_TYPE ||--o{ ASSET : classifies

    ASSET ||--o{ CALIBRATION_PLAN : has
    ASSET ||--o{ CALIBRATION_EVENT : undergoes
    CALIBRATION_PLAN o|--o{ CALIBRATION_EVENT : governs
    SUPPLIER o|--o{ CALIBRATION_EVENT : performs

    CALIBRATION_EVENT ||--o{ CERTIFICATE : produces
    ASSET ||--o{ CERTIFICATE : belongs_to

    ASSET ||--o{ WORK_ORDER : has
    CALIBRATION_EVENT o|--o{ WORK_ORDER : triggers

    ASSET ||--o{ PRODUCTION_USE : records

    ASSET ||--o{ EMERGENCY_EXTENSION : requests
    CALIBRATION_EVENT o|--o{ EMERGENCY_EXTENSION : relates_to
    EMERGENCY_EXTENSION o|--o{ PRODUCTION_USE : authorizes

    CALIBRATION_EVENT ||--o{ IMPACT_ASSESSMENT : requires
    ASSET ||--o{ IMPACT_ASSESSMENT : concerns
    WORK_ORDER o|--o{ IMPACT_ASSESSMENT : supports

    ASSET ||--o{ ALERT : generates
    CALIBRATION_EVENT o|--o{ ALERT : references
    PRODUCTION_USE o|--o{ ALERT : references

    INSTRUMENT_TYPE {
        int instrument_type_id PK
        varchar type_name UK
        text description
    }

    ASSET {
        varchar asset_id PK
        int instrument_type_id FK
        varchar asset_name
        varchar location
        varchar status
    }

    SUPPLIER {
        int supplier_id PK
        varchar supplier_name
        varchar contact_person
        varchar email
        varchar phone
    }

    CALIBRATION_PLAN {
        int plan_id PK
        varchar asset_id FK
        int interval_days
        date effective_from
        date effective_to
        enum status
    }

    CALIBRATION_EVENT {
        varchar calibration_id PK
        varchar asset_id FK
        int plan_id FK
        int supplier_id FK
        date calibration_date
        date due_date
        enum result
        decimal measured_value
        enum status
    }

    CERTIFICATE {
        varchar certificate_id PK
        varchar calibration_id FK
        varchar asset_id FK
        varchar certificate_number UK
        date issue_date
        date expiry_date
        enum status
    }

    WORK_ORDER {
        varchar work_order_id PK
        varchar asset_id FK
        varchar calibration_id FK
        varchar work_type
        datetime start_date
        datetime end_date
        int downtime_minutes
        enum status
    }

    PRODUCTION_USE {
        varchar use_id PK
        varchar asset_id FK
        varchar exception_reference FK
        datetime use_start
        datetime use_end
        varchar production_line
    }

    EMERGENCY_EXTENSION {
        varchar extension_reference PK
        varchar asset_id FK
        varchar calibration_id FK
        datetime valid_from
        datetime valid_to
        enum status
        varchar requested_by
        varchar approved_by
    }

    IMPACT_ASSESSMENT {
        varchar assessment_id PK
        varchar calibration_id FK
        varchar asset_id FK
        varchar work_order_id FK
        enum assessment_status
        enum impact_category
        datetime affected_from
        datetime affected_to
    }

    ALERT {
        bigint alert_id PK
        varchar asset_id FK
        varchar calibration_id FK
        varchar use_id FK
        varchar alert_type
        enum severity
        enum status
    }

    AUDIT_RECORD {
        bigint audit_id PK
        varchar entity_name
        varchar entity_id
        enum action
        json old_values
        json new_values
        datetime changed_at
        varchar changed_by
    }
```

## Relationship notes

1. One instrument type can classify multiple assets.
2. One asset can have multiple calibration plans and calibration events.
3. A calibration event can optionally reference one calibration plan and one supplier.
4. A calibration event can have multiple certificates.
5. A failed calibration can be associated with corrective work orders and impact assessments.
6. An asset can have multiple production-use records and emergency extensions.
7. A production-use record can optionally reference one emergency extension.
8. Alerts reference an asset and can optionally reference a calibration event or production-use record.
9. Audit records store historical changes across entities.

## Special database constraints

- `calibration_event` has a composite unique key on `(calibration_id, asset_id)`.
- `certificate` uses a composite foreign key to ensure its asset matches its calibration event.
- `emergency_extension` also uses a composite foreign key to ensure the calibration belongs to the same asset.
- `calibration_event` uses a composite foreign key to ensure its selected plan belongs to the same asset.
- `audit_record` intentionally has no direct foreign key because it stores changes for multiple entity types.
