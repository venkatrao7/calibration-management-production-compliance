
USE calibration_management;

-- Ensure each calibration plan and asset combination is unique.
ALTER TABLE calibration_plan
ADD CONSTRAINT uq_plan_asset
UNIQUE (plan_id, asset_id);

-- Ensure each calibration event and asset combination is unique.
ALTER TABLE calibration_event
ADD CONSTRAINT uq_calibration_asset
UNIQUE (calibration_id, asset_id);

-- Ensure a calibration event uses a plan belonging to the same asset.
ALTER TABLE calibration_event
ADD CONSTRAINT fk_event_plan_asset
FOREIGN KEY (plan_id, asset_id)
REFERENCES calibration_plan (plan_id, asset_id);

-- Ensure a certificate belongs to the same asset as its calibration event.
ALTER TABLE certificate
ADD CONSTRAINT fk_certificate_calibration_asset
FOREIGN KEY (calibration_id, asset_id)
REFERENCES calibration_event (calibration_id, asset_id);
