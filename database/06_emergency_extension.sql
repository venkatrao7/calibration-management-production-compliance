
USE calibration_management;

CREATE TABLE IF NOT EXISTS emergency_extension (
    extension_reference VARCHAR(100) PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    calibration_id VARCHAR(60),
    valid_from DATETIME NOT NULL,
    valid_to DATETIME NOT NULL,
    reason TEXT NOT NULL,
    status ENUM(
        'PENDING',
        'APPROVED',
        'REJECTED',
        'REVOKED'
    ) NOT NULL DEFAULT 'PENDING',
    requested_by VARCHAR(100) NOT NULL,
    approved_by VARCHAR(100),
    approved_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_extension_asset
        FOREIGN KEY (asset_id)
        REFERENCES asset(asset_id),

    CONSTRAINT fk_extension_calibration_asset
        FOREIGN KEY (calibration_id, asset_id)
        REFERENCES calibration_event(calibration_id, asset_id),

    CONSTRAINT chk_extension_dates
        CHECK (valid_to >= valid_from),

    CONSTRAINT chk_extension_approval
        CHECK (
            status <> 'APPROVED'
            OR (
                approved_by IS NOT NULL
                AND approved_at IS NOT NULL
            )
        )
);

ALTER TABLE production_use
ADD CONSTRAINT fk_production_use_extension
FOREIGN KEY (exception_reference)
REFERENCES emergency_extension(extension_reference);
