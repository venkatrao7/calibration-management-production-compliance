USE calibration_management;

CREATE TABLE asset (
    asset_id VARCHAR(20) PRIMARY KEY,
    instrument_type_id INT NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instrument_type_id)
        REFERENCES instrument_type(instrument_type_id)
);