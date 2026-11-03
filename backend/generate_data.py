"""
Deterministic synthetic data generator.
Run from the project root:
    python backend/generate_data.py

Writes CSV and JSON datasets to data/generated/.
Baseline relational datasets remain valid. Four deliberately anomalous
scenario fixtures and their labels are written separately.
"""
from pathlib import Path
from datetime import date, datetime, timedelta
from bisect import bisect_right
import hashlib
import json
import random
import argparse
import numpy as np
import pandas as pd

SEED = 20261022
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)
INSTRUMENT_COUNT = 2000
CALIBRATION_COUNT = 5000
PRODUCTION_USE_COUNT = 100000

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "generated"


def write_dataset(name, rows):
    empty_dataset_columns = {
        "alert": [
            "alert_id",
            "asset_id",
            "calibration_id",
            "use_id",
            "alert_type",
            "severity",
            "message",
            "status",
            "created_at",
            "resolved_at"
        ]
    }

    if rows:
        frame = pd.DataFrame(rows)
    else:
        frame = pd.DataFrame(
            columns=empty_dataset_columns.get(name, [])
        )

    frame.to_csv(OUT / f"{name}.csv", index=False)

    frame.to_json(
        OUT / f"{name}.json",
        orient="records",
        indent=2,
        date_format="iso"
    )

    return frame


def main():
    global SEED, INSTRUMENT_COUNT
    global CALIBRATION_COUNT, PRODUCTION_USE_COUNT, OUT

    parser = argparse.ArgumentParser(
        description="Generate deterministic calibration datasets."
    )

    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--assets", type=int, default=2000)
    parser.add_argument("--calibrations", type=int, default=5000)
    parser.add_argument("--production-uses", type=int, default=100000)
    parser.add_argument("--output-dir", type=Path, default=OUT)

    args = parser.parse_args()

    if min(args.assets, args.calibrations, args.production_uses) < 1:
        parser.error("All dataset counts must be greater than zero.")

    SEED = args.seed
    INSTRUMENT_COUNT = args.assets
    CALIBRATION_COUNT = args.calibrations
    PRODUCTION_USE_COUNT = args.production_uses
    OUT = args.output_dir.resolve()
    
    random.seed(SEED)
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Instrument types (parent/master data)
    type_names = [
        "Pressure Gauge", "Temperature Sensor", "Digital Multimeter",
        "Flow Meter", "Weighing Scale", "Torque Wrench",
        "pH Meter", "Vernier Caliper"
    ]
    instrument_types = [
        {
            "instrument_type_id": i,
            "type_name": name,
            "description": f"Synthetic {name.lower()} instrument type",
            "created_at": "2026-01-01 00:00:00"
        }
        for i, name in enumerate(type_names, start=1)
    ]

    # 2. Assets
    assets = []
    for i in range(1, INSTRUMENT_COUNT + 1):
        assets.append({
            "asset_id": f"AST-{i:06d}",
            "instrument_type_id": random.randint(1, len(type_names)),
            "asset_name": f"Instrument {i:04d}",
            "location": f"Plant-{random.randint(1, 5)} / Line-{random.randint(1, 20)}",
            "status": random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "INACTIVE"]),
            "created_at": "2026-01-01 00:00:00"
        })
    asset_ids = [row["asset_id"] for row in assets]

    # 3. Suppliers
    suppliers = [
        {
            "supplier_id": i,
            "supplier_name": f"Calibration Supplier {i}",
            "contact_person": f"Contact {i}",
            "email": f"supplier{i}@example.test",
            "phone": f"900000{i:04d}",
            "created_at": "2026-01-01 00:00:00"
        }
        for i in range(1, 21)
    ]

    # 4. One active calibration plan per asset
    plans = []
    plan_by_asset = {}
    for i, asset_id in enumerate(asset_ids, start=1):
        plan = {
            "plan_id": i,
            "asset_id": asset_id,
            "interval_days": random.choice([30, 60, 90, 180, 365]),
            "effective_from": START_DATE.isoformat(),
            "effective_to": None,
            "status": "ACTIVE",
            "created_at": "2026-01-01 00:00:00"
        }
        plans.append(plan)
        plan_by_asset[asset_id] = plan

    # 5. Calibration events: due dates are derived from the applicable plan.
    calibrations = []
    calibration_by_id = {}
    calibrations_by_asset = {asset_id: [] for asset_id in asset_ids}

    for i in range(1, CALIBRATION_COUNT + 1):
        asset_id = asset_ids[(i - 1) % len(asset_ids)]
        plan = plan_by_asset[asset_id]
        cal_date = START_DATE + timedelta(days=random.randint(0, 300))
        due_date = cal_date + timedelta(days=plan["interval_days"])
        result = random.choices(["PASS", "FAIL"], weights=[90, 10])[0]
        calibration_id = f"CAL-{asset_id}-2026-{i:06d}"

        row = {
            "calibration_id": calibration_id,
            "asset_id": asset_id,
            "plan_id": plan["plan_id"],
            "supplier_id": random.randint(1, len(suppliers)),
            "calibration_date": cal_date.isoformat(),
            "due_date": due_date.isoformat(),
            "result": result,
            "measured_value": round(float(np.random.normal(100, 2)), 4),
            "performed_by": f"Technician {random.randint(1, 30)}",
            "status": "COMPLETED",
            "created_at": "2026-01-01 00:00:00"
        }
        calibrations.append(row)
        calibration_by_id[calibration_id] = row
        calibrations_by_asset[asset_id].append(row)

    for rows in calibrations_by_asset.values():
        rows.sort(key=lambda row: row["calibration_date"])

    # 6. Certificates. Every successful calibration gets a certificate.
    certificates = []
    certificate_number = 1

    for cal in calibrations:
        if cal["result"] == "PASS":
            certificates.append({
                "certificate_id": f"CERT-{cal['calibration_id']}",
                "calibration_id": cal["calibration_id"],
                "asset_id": cal["asset_id"],
                "certificate_number": f"CERT-NO-{certificate_number:07d}",
                "issue_date": cal["calibration_date"],
                "expiry_date": cal["due_date"],
                "file_reference": f"certificates/{cal['calibration_id']}.pdf",
                "status": "VALID",
                "created_at": "2026-01-01 00:00:00"
            })
            certificate_number += 1

    # 7. Work orders. Every failed baseline calibration gets an impact/
    # corrective-action work order.
    work_orders = []
    work_order_number = 1
    for cal in calibrations:
        if cal["result"] == "FAIL":
            start = datetime.fromisoformat(cal["calibration_date"] + " 09:00:00")
            work_orders.append({
                "work_order_id": f"WO-2026-{work_order_number:06d}",
                "asset_id": cal["asset_id"],
                "calibration_id": cal["calibration_id"],
                "work_type": "CORRECTIVE_ACTION",
                "start_date": start.isoformat(sep=" "),
                "end_date": (start + timedelta(hours=2)).isoformat(sep=" "),
                "downtime_minutes": 120,
                "status": "COMPLETED",
                "description": "Impact assessment and corrective action for failed calibration",
                "created_at": "2026-01-01 00:00:00"
            })
            work_order_number += 1

    
    # 8. Production use. Generate records only inside a valid
    # passing calibration window for the asset.
    production_uses = []
    used_ids = set()

    eligible_windows = []

    for asset_id, history in calibrations_by_asset.items():
        sorted_history = sorted(
            history,
            key=lambda row: row["calibration_date"]
        )

        for index, cal in enumerate(sorted_history):
            if cal["result"] != "PASS":
                continue

            window_start = date.fromisoformat(cal["calibration_date"])
            window_end = min(
                date.fromisoformat(cal["due_date"]),
                END_DATE
            )

            # A later calibration supersedes the previous calibration.
            if index + 1 < len(sorted_history):
                next_calibration_date = date.fromisoformat(
                    sorted_history[index + 1]["calibration_date"]
                )
                window_end = min(
                    window_end,
                    next_calibration_date - timedelta(days=1)
                )

            if window_end >= window_start:
                eligible_windows.append({
                    "asset_id": asset_id,
                    "start": window_start,
                    "end": window_end
                })

    if not eligible_windows:
        raise ValueError(
            "No valid passing calibration windows available."
        )

    for i in range(1, PRODUCTION_USE_COUNT + 1):
        window = random.choice(eligible_windows)
        asset_id = window["asset_id"]

        day_offset = random.randint(
            0,
            (window["end"] - window["start"]).days
        )
        use_date = window["start"] + timedelta(days=day_offset)

        start_dt = datetime.combine(
            use_date,
            datetime.min.time()
        ) + timedelta(
            minutes=random.randint(0, 1439),
            seconds=random.randint(0, 59)
        )

        use_id = f"USE-{asset_id}-{start_dt.strftime('%Y%m%d%H%M%S')}"

        while use_id in used_ids:
            start_dt += timedelta(seconds=1)
            use_id = f"USE-{asset_id}-{start_dt.strftime('%Y%m%d%H%M%S')}"

        used_ids.add(use_id)

        end_dt = start_dt + timedelta(minutes=random.randint(5, 240))

        production_uses.append({
            "use_id": use_id,
            "asset_id": asset_id,
            "use_start": start_dt.isoformat(sep=" "),
            "use_end": end_dt.isoformat(sep=" "),
            "production_line": f"Line-{random.randint(1, 20)}",
            "exception_reference": None,
            "created_at": "2026-01-01 00:00:00"
        })


    # 9. Alerts. Use per-asset sorted calibration history and binary search;
    # this avoids repeatedly scanning all 5,000 calibration events per use.
    alerts = []
    alert_id = 1
    for use in production_uses:
        use_date = datetime.fromisoformat(use["use_start"]).date()
        history = calibrations_by_asset[use["asset_id"]]
        history_dates = [
            date.fromisoformat(row["calibration_date"]) for row in history
        ]
        position = bisect_right(history_dates, use_date) - 1
        latest = history[position] if position >= 0 else None

        invalid = (
            latest is None
            or use_date > date.fromisoformat(latest["due_date"])
            or latest["result"] == "FAIL"
        )
        if invalid:
            alerts.append({
                "alert_id": alert_id,
                "asset_id": use["asset_id"],
                "calibration_id": latest["calibration_id"] if latest else None,
                "use_id": use["use_id"],
                "alert_type": "OUT_OF_CALIBRATION_USE",
                "severity": "HIGH",
                "message": "Production use occurred without a valid passing calibration window",
                "status": "OPEN",
                "created_at": use["use_start"],
                "resolved_at": None
            })
            alert_id += 1

    # 10. Audit records for generated entity creation events.
    audit_records = []
    audit_id = 1
    audit_sources = [
        ("asset", assets, "asset_id"),
        ("calibration_event", calibrations, "calibration_id"),
        ("certificate", certificates, "certificate_id"),
        ("work_order", work_orders, "work_order_id"),
        ("production_use", production_uses, "use_id")
    ]
    for table_name, records, key in audit_sources:
        for record in records:
            audit_records.append({
                "audit_id": audit_id,
                "entity_name": table_name,
                "entity_id": str(record[key]),
                "action": "INSERT",
                "old_values": None,
                "new_values": json.dumps(record, sort_keys=True),
                "changed_at": record.get("created_at", "2026-01-01 00:00:00"),
                "changed_by": "synthetic_generator"
            })
            audit_id += 1

    datasets = {
        "instrument_type": instrument_types,
        "asset": assets,
        "supplier": suppliers,
        "calibration_plan": plans,
        "calibration_event": calibrations,
        "certificate": certificates,
        "work_order": work_orders,
        "production_use": production_uses,
        "alert": alerts,
        "audit_record": audit_records
    }

    for name, rows in datasets.items():
        write_dataset(name, rows)

    # Anomaly fixtures are deliberately separate from clean baseline tables.
    # They provide concrete bad-value scenarios and separate ground-truth labels.
    first_cal = calibrations[0]
    first_plan = plan_by_asset[first_cal["asset_id"]]
    first_use = production_uses[0]
    first_certificate = certificates[0] if certificates else None
    failed_cal = next(row for row in calibrations if row["result"] == "FAIL")

    anomaly_fixtures = [
        {
            "case_id": "ANOM-001",
            "issue_type": "DUE_DATE_INCONSISTENT_WITH_PLAN",
            "entity_name": "calibration_event",
            "entity_id": first_cal["calibration_id"],
            "field_name": "due_date",
            "baseline_value": first_cal["due_date"],
            "anomalous_value": (
                date.fromisoformat(first_cal["due_date"]) + timedelta(days=1)
            ).isoformat()
        },
        {
            "case_id": "ANOM-002",
            "issue_type": "EXPIRED_INSTRUMENT_USED_WITHOUT_EXCEPTION",
            "entity_name": "production_use",
            "entity_id": first_use["use_id"],
            "field_name": "use_start",
            "baseline_value": first_use["use_start"],
            "anomalous_value": (
                datetime.combine(END_DATE, datetime.min.time()) +
                timedelta(hours=23, minutes=59)
            ).isoformat(sep=" ")
        },
        {
            "case_id": "ANOM-003",
            "issue_type": "CERTIFICATE_REFERS_TO_ANOTHER_ASSET",
            "entity_name": "certificate",
            "entity_id": first_certificate["certificate_id"] if first_certificate else "",
            "field_name": "asset_id",
            "baseline_value": first_certificate["asset_id"] if first_certificate else "",
            "anomalous_value": next(
                asset_id for asset_id in asset_ids
                if first_certificate and asset_id != first_certificate["asset_id"]
            ) if first_certificate else ""
        },
        {
            "case_id": "ANOM-004",
            "issue_type": "FAILED_CALIBRATION_WITHOUT_IMPACT_ASSESSMENT",
            "entity_name": "calibration_event",
            "entity_id": failed_cal["calibration_id"],
            "field_name": "impact_assessment_status",
            "baseline_value": "COMPLETED",
            "anomalous_value": None
        }
    ]

    ground_truth = [
        {
            "case_id": row["case_id"],
            "issue_type": row["issue_type"],
            "entity_name": row["entity_name"],
            "entity_id": row["entity_id"],
            "ground_truth": 1
        }
        for row in anomaly_fixtures
    ]
    write_dataset("anomaly_fixtures", anomaly_fixtures)
    write_dataset("ground_truth", ground_truth)

    # Baseline validation checks.
    asset_id_set = set(asset_ids)
    plan_ids = {row["plan_id"] for row in plans}
    supplier_ids = {row["supplier_id"] for row in suppliers}
    checks = {
        "asset_count_matches_configuration": len(assets) == INSTRUMENT_COUNT,
        "calibration_count_matches_configuration": len(calibrations) == CALIBRATION_COUNT,
        "production_use_count_matches_configuration": len(production_uses) == PRODUCTION_USE_COUNT,
        "asset_ids_unique": len(asset_id_set) == len(assets),
        "calibration_ids_unique": len(calibration_by_id) == len(calibrations),
        "production_use_ids_unique": len(used_ids) == len(production_uses),
        "asset_type_foreign_keys_valid": all(
            1 <= row["instrument_type_id"] <= len(instrument_types) for row in assets
        ),
        "calibration_asset_foreign_keys_valid": all(
            row["asset_id"] in asset_id_set for row in calibrations
        ),
        "calibration_plan_foreign_keys_valid": all(
            row["plan_id"] in plan_ids and row["asset_id"] == plans[row["plan_id"] - 1]["asset_id"]
            for row in calibrations
        ),
        "calibration_supplier_foreign_keys_valid": all(
            row["supplier_id"] in supplier_ids for row in calibrations
        ),
        "certificate_asset_matches_calibration": all(
            calibration_by_id[row["calibration_id"]]["asset_id"] == row["asset_id"]
            for row in certificates
        ),
        "calibration_due_dates_derived_from_plan": all(
            date.fromisoformat(row["due_date"]) ==
            date.fromisoformat(row["calibration_date"]) +
            timedelta(days=plan_by_asset[row["asset_id"]]["interval_days"])
            for row in calibrations
        ),
        "every_failed_calibration_has_work_order": all(
            any(wo["calibration_id"] == row["calibration_id"] for wo in work_orders)
            for row in calibrations if row["result"] == "FAIL"
        ),
        "ground_truth_has_four_cases": len(ground_truth) == 4
    }

    row_counts = {name: len(rows) for name, rows in datasets.items()}
    summary = {
        "seed": SEED,
        "period": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat()},
        "row_counts": row_counts,
        "validations": checks,
        "all_validations_passed": all(checks.values()),
        "note": "Anomaly scenarios are stored separately in anomaly_fixtures and ground_truth."
    }
    (OUT / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    manifest = []
    for path in sorted(OUT.glob("*")):
        if path.is_file() and path.name != "source_manifest.json":
            manifest.append({
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            })
    (OUT / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"Generated datasets in: {OUT}")
    print(json.dumps(summary, indent=2))
    if not all(checks.values()):
        raise SystemExit("One or more validation checks failed.")


if __name__ == "__main__":
    main()
