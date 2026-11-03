
USE calibration_management;

-- 4. Calibration Plan
CREATE TABLE IF NOT EXISTS calibration_plan (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    interval_days INT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    CHECK (interval_days > 0),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

-- 5. Calibration Event
CREATE TABLE IF NOT EXISTS calibration_event (
    calibration_id VARCHAR(60) PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    plan_id INT,
    supplier_id INT,
    calibration_date DATE NOT NULL,
    due_date DATE NOT NULL,
    result ENUM('PASS', 'FAIL') NOT NULL,
    measured_value DECIMAL(12,4),
    performed_by VARCHAR(100),
    status ENUM('COMPLETED', 'CANCELLED') DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    FOREIGN KEY (plan_id) REFERENCES calibration_plan(plan_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    CHECK (due_date >= calibration_date)
);

-- 6. Certificate
CREATE TABLE IF NOT EXISTS certificate (
    certificate_id VARCHAR(80) PRIMARY KEY,
    calibration_id VARCHAR(60) NOT NULL,
    asset_id VARCHAR(20) NOT NULL,
    certificate_number VARCHAR(100) NOT NULL UNIQUE,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    file_reference VARCHAR(255),
    status ENUM('VALID', 'EXPIRED', 'REVOKED') DEFAULT 'VALID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calibration_id) REFERENCES calibration_event(calibration_id),
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    CHECK (expiry_date IS NULL OR expiry_date >= issue_date)
);

-- 7. Work Order
CREATE TABLE IF NOT EXISTS work_order (
    work_order_id VARCHAR(30) PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    calibration_id VARCHAR(60),
    work_type VARCHAR(50) NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME,
    downtime_minutes INT DEFAULT 0,
    status ENUM('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'OPEN',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    FOREIGN KEY (calibration_id) REFERENCES calibration_event(calibration_id),
    CHECK (downtime_minutes >= 0),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- 8. Production Use
CREATE TABLE IF NOT EXISTS production_use (
    use_id VARCHAR(80) PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    use_start DATETIME NOT NULL,
    use_end DATETIME,
    production_line VARCHAR(100),
    exception_reference VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    CHECK (use_end IS NULL OR use_end >= use_start)
);

-- 9. Alert
CREATE TABLE IF NOT EXISTS alert (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    asset_id VARCHAR(20) NOT NULL,
    calibration_id VARCHAR(60),
    use_id VARCHAR(80),
    alert_type VARCHAR(60) NOT NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    message TEXT NOT NULL,
    status ENUM('OPEN', 'ACKNOWLEDGED', 'RESOLVED') DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (asset_id) REFERENCES asset(asset_id),
    FOREIGN KEY (calibration_id) REFERENCES calibration_event(calibration_id),
    FOREIGN KEY (use_id) REFERENCES production_use(use_id)
);

-- 10. Audit Record
CREATE TABLE IF NOT EXISTS audit_record (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_name VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action ENUM('INSERT', 'UPDATE', 'DELETE', 'STATUS_CHANGE') NOT NULL,
    old_values JSON,
    new_values JSON,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100)
);
