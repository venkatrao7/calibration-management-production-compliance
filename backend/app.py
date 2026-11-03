
from datetime import date
from decimal import Decimal

from flask import Flask, jsonify, request

from db import get_db_connection
from services.compliance_service import run_compliance_checks
from services.asset_service import (
    list_assets,
    get_asset,
    get_instrument_types,
    create_asset,
    update_asset,
    change_asset_status,
)
from services.calibration_service import (
    list_calibration_plans,
    get_calibration_plan,
    create_calibration_plan,
)
from services.calibration_service import (
    list_calibration_events,
    get_calibration_event,
    schedule_calibration,
    complete_calibration,
    cancel_calibration,
)
from services.calibration_service import (
    list_certificates,
    get_certificate,
    generate_certificate,
)
from services.production_use_service import (
    list_production_uses,
    create_production_use
)
from services.compliance_service import get_production_use_violations
from services.work_order_service import (
    list_work_orders,
    create_work_order
)
from services.impact_assessment_service import (
    list_assessments,
    create_assessment,
    complete_assessment
)
from services.work_order_service import update_work_order_status
app = Flask(__name__)


def make_json_safe(value):
    """Convert MySQL date/time and decimal values into JSON-safe values."""
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, (date,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def get_connection():
    connection = get_db_connection()
    if connection is None:
        return None
    return connection


@app.route("/")
def home():
    return jsonify({
        "message": "Calibration Management and Production Compliance System",
        "status": "Backend is running successfully"
    })


@app.route("/test-db")
def test_database():
    connection = get_connection()
    if connection is None:
        return jsonify({"message": "MySQL connection failed"}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]
        cursor.close()

        return jsonify({
            "message": "MySQL connected successfully",
            "database": database_name
        })
    finally:
        connection.close()


# --------------------------------------------------
# COMPLIANCE APIs
# --------------------------------------------------

@app.route("/api/compliance/checks", methods=["GET"])
def compliance_checks():
    """Run read-only compliance checks."""
    as_of_text = request.args.get("as_of_date")
    as_of_date = None

    if as_of_text:
        try:
            as_of_date = date.fromisoformat(as_of_text)
        except ValueError:
            return jsonify({
                "error": "Invalid as_of_date. Use YYYY-MM-DD."
            }), 400

    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        findings = run_compliance_checks(connection, as_of_date)

        response = {
            "as_of_date": findings["as_of_date"],
            "summary": {},
            "sample_limit": 100,
            "findings": {}
        }

        for finding_name, records in findings.items():
            if finding_name == "as_of_date":
                continue

            response["summary"][finding_name] = len(records)
            response["findings"][finding_name] = records[:100]

        return jsonify(make_json_safe(response))

    except Exception:
        app.logger.exception("Compliance checks failed")
        return jsonify({
            "error": "Compliance checks could not be completed."
        }), 500

    finally:
        connection.close()


# --------------------------------------------------
# INSTRUMENT TYPE API
# --------------------------------------------------

@app.route("/api/instrument-types", methods=["GET"])
def instrument_types():
    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        records = get_instrument_types(connection)
        return jsonify({
            "count": len(records),
            "instrument_types": make_json_safe(records)
        })
    except Exception:
        app.logger.exception("Could not retrieve instrument types")
        return jsonify({"error": "Could not retrieve instrument types."}), 500
    finally:
        connection.close()


# --------------------------------------------------
# ASSET MANAGEMENT APIs
# --------------------------------------------------

@app.route("/api/assets", methods=["GET"])
def assets_list():
    """List, search, filter and paginate assets."""
    search = request.args.get("search")
    status = request.args.get("status")
    instrument_type = request.args.get("instrument_type_id")

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        if limit < 1 or limit > 500:
            return jsonify({"error": "Limit must be between 1 and 500."}), 400

        if offset < 0:
            return jsonify({"error": "Offset cannot be negative."}), 400

        instrument_type_id = None
        if instrument_type:
            instrument_type_id = int(instrument_type)
            if instrument_type_id < 1:
                raise ValueError

    except ValueError:
        return jsonify({
            "error": "Invalid pagination or instrument_type_id parameter."
        }), 400

    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        result = list_assets(
            connection,
            search=search,
            status=status,
            instrument_type_id=instrument_type_id,
            limit=limit,
            offset=offset
        )
        return jsonify(make_json_safe(result))

    except Exception:
        app.logger.exception("Could not retrieve assets")
        return jsonify({"error": "Could not retrieve assets."}), 500

    finally:
        connection.close()


@app.route("/api/assets/<string:asset_id>", methods=["GET"])
def asset_detail(asset_id):
    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        asset = get_asset(connection, asset_id)

        if not asset:
            return jsonify({"error": "Asset not found."}), 404

        return jsonify(make_json_safe(asset))

    except Exception:
        app.logger.exception("Could not retrieve asset")
        return jsonify({"error": "Could not retrieve asset."}), 500

    finally:
        connection.close()


@app.route("/api/assets", methods=["POST"])
def asset_create():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON request body is required."}), 400

    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        asset = create_asset(connection, data)

        return jsonify({
            "message": "Asset created successfully.",
            "asset": make_json_safe(asset)
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Asset creation failed")
        return jsonify({"error": "Asset could not be created."}), 500

    finally:
        connection.close()


@app.route("/api/assets/<string:asset_id>", methods=["PUT"])
def asset_update(asset_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON request body is required."}), 400

    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        asset = update_asset(connection, asset_id, data)

        if not asset:
            return jsonify({"error": "Asset not found."}), 404

        return jsonify({
            "message": "Asset updated successfully.",
            "asset": make_json_safe(asset)
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Asset update failed")
        return jsonify({"error": "Asset could not be updated."}), 500

    finally:
        connection.close()


@app.route("/api/assets/<string:asset_id>/status", methods=["PATCH"])
def asset_status_update(asset_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or "status" not in data:
        return jsonify({
            "error": "Provide a status field with ACTIVE or INACTIVE."
        }), 400

    status = data.get("status")
    changed_by = data.get("changed_by", "SYSTEM")

    connection = get_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        asset = change_asset_status(
            connection,
            asset_id,
            status,
            changed_by
        )

        if not asset:
            return jsonify({"error": "Asset not found."}), 404

        return jsonify({
            "message": "Asset status updated successfully.",
            "asset": make_json_safe(asset)
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Asset status update failed")
        return jsonify({"error": "Asset status could not be updated."}), 500

    finally:
        connection.close()

# --------------------------------------------------
# CALIBRATION PLAN APIs
# --------------------------------------------------

@app.route("/api/calibration-plans", methods=["GET"])
def calibration_plans_list():
    search = request.args.get("search")
    status = request.args.get("status")

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        if limit < 1 or limit > 500:
            return jsonify({"error": "Limit must be between 1 and 500."}), 400

        if offset < 0:
            return jsonify({"error": "Offset cannot be negative."}), 400

    except ValueError:
        return jsonify({"error": "Invalid pagination values."}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        result = list_calibration_plans(
            connection,
            search=search,
            status=status,
            limit=limit,
            offset=offset
        )
        return jsonify(make_json_safe(result))

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Could not retrieve calibration plans")
        return jsonify({"error": "Could not retrieve calibration plans."}), 500

    finally:
        connection.close()


@app.route("/api/calibration-plans/<int:plan_id>", methods=["GET"])
def calibration_plan_detail(plan_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        plan = get_calibration_plan(connection, plan_id)

        if not plan:
            return jsonify({"error": "Calibration plan not found."}), 404

        return jsonify(make_json_safe(plan))

    except Exception:
        app.logger.exception("Could not retrieve calibration plan")
        return jsonify({"error": "Could not retrieve calibration plan."}), 500

    finally:
        connection.close()


@app.route("/api/calibration-plans", methods=["POST"])
def calibration_plan_create():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON request body is required."}), 400

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Could not connect to MySQL."}), 500

    try:
        plan = create_calibration_plan(connection, data)

        return jsonify({
            "message": "Calibration plan created successfully.",
            "plan": make_json_safe(plan)
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Calibration plan creation failed")
        return jsonify({"error": "Calibration plan could not be created."}), 500

    finally:
        connection.close()

# ============================================================
# CALIBRATION EVENT API ROUTES
# ============================================================

@app.route("/api/calibration-events", methods=["GET"])
def api_list_calibration_events():
    connection = get_db_connection()

    try:
        result = list_calibration_events(
            connection,
            search=request.args.get("search"),
            status=request.args.get("status"),
            result=request.args.get("result"),
            limit=request.args.get("limit", 10),
            offset=request.args.get("offset", 0)
        )
        return jsonify(make_json_safe(result)), 200

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    finally:
        connection.close()


@app.route("/api/calibration-events/<calibration_id>", methods=["GET"])
def api_get_calibration_event(calibration_id):
    connection = get_db_connection()

    try:
        event = get_calibration_event(connection, calibration_id)

        if not event:
            return jsonify({"error": "Calibration event not found."}), 404

        return jsonify(make_json_safe(event)), 200

    finally:
        connection.close()


@app.route("/api/calibration-events", methods=["POST"])
def api_schedule_calibration():
    connection = get_db_connection()

    try:
        data = request.get_json(silent=True) or {}
        event = schedule_calibration(connection, data)

        return jsonify({
            "message": "Calibration scheduled successfully.",
            "event": make_json_safe(event)
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        connection.close()


@app.route(
    "/api/calibration-events/<calibration_id>/complete",
    methods=["PATCH"]
)
def api_complete_calibration(calibration_id):
    connection = get_db_connection()

    try:
        data = request.get_json(silent=True) or {}

        event = complete_calibration(
            connection,
            calibration_id,
            data
        )

        return jsonify({
            "message": "Calibration completed successfully.",
            "event": make_json_safe(event)
        }), 200

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        connection.close()


@app.route(
    "/api/calibration-events/<calibration_id>/cancel",
    methods=["PATCH"]
)
def api_cancel_calibration(calibration_id):
    connection = get_db_connection()

    try:
        data = request.get_json(silent=True) or {}

        event = cancel_calibration(
            connection,
            calibration_id,
            data
        )

        return jsonify({
            "message": "Calibration cancelled successfully.",
            "event": make_json_safe(event)
        }), 200

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        connection.close()


# ============================================================
# CERTIFICATE MANAGEMENT API ROUTES
# ============================================================

@app.route("/api/certificates", methods=["GET"])
def api_list_certificates():
    connection = get_db_connection()

    try:
        result = list_certificates(
            connection,
            search=request.args.get("search"),
            status=request.args.get("status"),
            limit=request.args.get("limit", 10),
            offset=request.args.get("offset", 0)
        )

        return jsonify(make_json_safe(result)), 200

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    finally:
        connection.close()


@app.route("/api/certificates/<certificate_id>", methods=["GET"])
def api_get_certificate(certificate_id):
    connection = get_db_connection()

    try:
        certificate = get_certificate(connection, certificate_id)

        if not certificate:
            return jsonify({
                "error": "Certificate not found."
            }), 404

        return jsonify(make_json_safe(certificate)), 200

    finally:
        connection.close()


@app.route(
    "/api/calibration-events/<calibration_id>/generate-certificate",
    methods=["POST"]
)
def api_generate_certificate(calibration_id):
    connection = get_db_connection()

    try:
        data = request.get_json(silent=True) or {}

        certificate = generate_certificate(
            connection,
            calibration_id,
            data
        )

        return jsonify({
            "message": "Certificate generated successfully.",
            "certificate": make_json_safe(certificate)
        }), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    finally:
        connection.close()
@app.route("/api/production-uses", methods=["GET"])
def api_list_production_uses():
    connection = get_db_connection()

    try:
        search = request.args.get("search")
        limit = min(int(request.args.get("limit", 100)), 500)
        offset = max(int(request.args.get("offset", 0)), 0)

        result = list_production_uses(
            connection,
            search=search,
            limit=limit,
            offset=offset
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()


@app.route("/api/production-uses", methods=["POST"])
def api_create_production_use():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = create_production_use(
            data,
            changed_by=data.get("changed_by", "System")
        )

        return jsonify(result), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production-uses/violations", methods=["GET"])
def api_production_use_violations():
    connection = get_db_connection()

    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        violations = get_production_use_violations(
            connection,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            "total": len(violations),
            "violations": violations
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()
@app.route("/api/work-orders", methods=["GET"])
def api_list_work_orders():
    connection = get_db_connection()

    try:
        search = request.args.get("search")
        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 100)), 500)
        offset = max(int(request.args.get("offset", 0)), 0)

        valid_statuses = {
            "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"
        }

        if status and status not in valid_statuses:
            return jsonify({"error": "Invalid work order status"}), 400

        result = list_work_orders(
            connection,
            search=search,
            status=status,
            limit=limit,
            offset=offset
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()


@app.route("/api/work-orders", methods=["POST"])
def api_create_work_order():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = create_work_order(
            data,
            changed_by=data.get("changed_by", "System")
        )

        return jsonify(result), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/impact-assessments", methods=["GET"])
def api_list_impact_assessments():
    connection = get_db_connection()

    try:
        search = request.args.get("search")
        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 100)), 500)
        offset = max(int(request.args.get("offset", 0)), 0)

        result = list_assessments(
            connection,
            search=search,
            status=status,
            limit=limit,
            offset=offset
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


@app.route("/api/impact-assessments", methods=["POST"])
def api_create_impact_assessment():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = create_assessment(
            data,
            changed_by=data.get("changed_by", "System")
        )

        return jsonify(result), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route(
    "/api/impact-assessments/<assessment_id>/complete",
    methods=["PATCH"]
)
def api_complete_impact_assessment(assessment_id):
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = complete_assessment(
            assessment_id,
            data,
            changed_by=data.get("changed_by", "Quality Engineer")
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/api/work-orders/<work_order_id>/status", methods=["PATCH"])
def api_update_work_order_status(work_order_id):
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        result = update_work_order_status(
            work_order_id,
            data,
            changed_by=data.get("changed_by", "Maintenance Engineer")
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    app.run(debug=True)
