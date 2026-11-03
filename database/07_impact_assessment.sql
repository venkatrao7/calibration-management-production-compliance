
USE calibration_management;

CREATE TABLE impact_assessment (
    assessment_id VARCHAR(50) PRIMARY KEY,

    calibration_id VARCHAR(60) NOT NULL,
    asset_id VARCHAR(20) NOT NULL,
    work_order_id VARCHAR(30),

    assessment_status ENUM(
        'DRAFT',
        'COMPLETED'
    ) NOT NULL DEFAULT 'DRAFT',

    impact_category ENUM(
        'NO_IMPACT',
        'PRODUCT_HOLD',
        'REWORK_REQUIRED',
        'RECALL_REQUIRED',
        'INVESTIGATION_REQUIRED'
    ),

    affected_from DATETIME,
    affected_to DATETIME,

    disposition TEXT,
    notes TEXT,

    assessed_by VARCHAR(100),
    assessed_at DATETIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_impact_calibration_asset
        FOREIGN KEY (calibration_id, asset_id)
        REFERENCES calibration_event(calibration_id, asset_id),

    CONSTRAINT fk_impact_work_order
        FOREIGN KEY (work_order_id)
        REFERENCES work_order(work_order_id),

    CONSTRAINT chk_impact_dates
        CHECK (
            affected_to IS NULL
            OR affected_from IS NULL
            OR affected_to >= affected_from
        ),

    CONSTRAINT chk_completed_assessment
        CHECK (
            assessment_status <> 'COMPLETED'
            OR (
                impact_category IS NOT NULL
                AND disposition IS NOT NULL
                AND assessed_by IS NOT NULL
                AND assessed_at IS NOT NULL
            )
        )
);
