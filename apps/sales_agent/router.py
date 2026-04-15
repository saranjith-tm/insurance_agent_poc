from flask import Blueprint, render_template, jsonify, request, current_app
from apps.sales_agent import crud
from apps.sales_agent import service

sales_agent_bp = Blueprint("sales_agent", __name__)


@sales_agent_bp.route("/")
def queue_view():
    cases = crud.get_all_cases()
    stats = service.get_queue_stats(cases)
    return render_template("queue.html", cases=cases, stats=stats)


@sales_agent_bp.route("/case/<app_no>")
@sales_agent_bp.route("/case/<app_no>/<tab>")
def case_view(app_no, tab="single"):
    case = crud.get_case(app_no)
    if not case:
        return "Case not found", 404
    return render_template("case.html", data=case, active_tab=tab)


@sales_agent_bp.route("/case/<app_no>/docs")
def doc_viewer(app_no):
    case = crud.get_case(app_no)
    if not case:
        return "Case not found", 404

    doc_files = service.get_doc_files(app_no, current_app.static_folder)
    return render_template("doc_viewer.html", data=case, doc_files=doc_files)


@sales_agent_bp.route("/case/<app_no>/audit")
def audit_view(app_no):
    case = crud.get_case(app_no)
    if not case:
        return "Case not found", 404
    log = crud.get_audit_log(app_no)
    history = crud.get_submission_history(app_no)
    return render_template(
        "audit.html", data=case, audit_log=log, submission_history=history
    )


# API endpoints
@sales_agent_bp.route("/api/applicant/<app_no>")
def get_applicant_data(app_no):
    case = crud.get_case(app_no)
    if not case:
        return jsonify({"error": "Not found"}), 404
    return jsonify(case)


@sales_agent_bp.route("/api/cases")
def get_cases():
    status_filter = request.args.get("status")
    cases = crud.get_all_cases()
    if status_filter:
        cases = [c for c in cases if c["status"] == status_filter]
    return jsonify(cases)


@sales_agent_bp.route("/api/case/<app_no>/status", methods=["GET"])
def get_case_status(app_no):
    case = crud.get_case(app_no)
    if not case:
        return jsonify({"error": "Not found"}), 404
    return jsonify(
        {
            "app_no": app_no,
            "status": case["status"],
            "uw_status": case["uw_status"],
            "uw_decision": case["uw_decision"],
            "updated_at": case["updated_at"],
        }
    )


@sales_agent_bp.route("/api/cases/statuses")
def get_all_statuses():
    cases = crud.get_all_cases()
    statuses_map = service.get_all_statuses_map(cases)
    return jsonify(statuses_map)


@sales_agent_bp.route("/api/case/<app_no>/audit")
def get_audit(app_no):
    return jsonify(crud.get_audit_log(app_no))
