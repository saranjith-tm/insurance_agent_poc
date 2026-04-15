from flask import Blueprint, render_template, jsonify, request
from apps.underwriting import crud
from apps.underwriting import service
from apps.underwriting.constants import FIELD_MAP, TEXT_FIELD_MAP

underwriting_bp = Blueprint("underwriting", __name__)


@underwriting_bp.route("/")
@underwriting_bp.route("/<app_no>")
def index(app_no="OS121345678"):
    state = crud.load_state(app_no)
    case = crud.get_case(app_no)
    return render_template("index.html", state=state, case=case)


@underwriting_bp.route("/api/state")
@underwriting_bp.route("/api/state/<app_no>")
def get_state(app_no="OS121345678"):
    state = crud.load_state(app_no)
    return jsonify(state)


@underwriting_bp.route("/api/reset", methods=["POST"])
def reset_state():
    data = request.json or {}
    app_no = data.get("app_no", "OS121345678")
    crud.reset_submission(app_no)
    return jsonify(
        {
            "status": "ok",
            "message": "State reset — a new submission will be created on next load",
        }
    )


@underwriting_bp.route("/api/click", methods=["POST"])
def handle_click():
    data = request.json
    element_id = data.get("element_id", "")
    value = data.get("value")
    app_no = data.get("app_no", "OS121345678")

    if element_id not in FIELD_MAP:
        return jsonify(
            {"status": "error", "message": f"Unknown element: {element_id}"}
        ), 400

    state = crud.load_state(app_no)
    path = FIELD_MAP[element_id]
    old_value = service.get_path_value(state, path)
    service.set_path_value(state, path, value)
    is_complete = service.update_completion_status(state)
    crud.save_state(state)

    if old_value != value:
        crud.log_field_update(app_no, element_id, str(old_value), str(value))

    return jsonify(
        {
            "status": "ok",
            "field": element_id,
            "value": value,
            "checklist_complete": is_complete,
            "submission_id": state.get("_submission_id"),
        }
    )


@underwriting_bp.route("/api/fill", methods=["POST"])
def fill_text():
    data = request.json
    element_id = data.get("element_id", "")
    value = data.get("value", "")
    app_no = data.get("app_no", "OS121345678")

    if element_id not in TEXT_FIELD_MAP:
        return jsonify(
            {"status": "error", "message": f"Unknown field: {element_id}"}
        ), 400

    state = crud.load_state(app_no)
    path = TEXT_FIELD_MAP[element_id]
    old_value = service.get_path_value(state, path)
    service.set_path_value(state, path, value)
    service.update_completion_status(state)
    crud.save_state(state)

    if old_value != value and value:
        crud.log_field_update(app_no, element_id, str(old_value), str(value))

    return jsonify({"status": "ok", "field": element_id, "value": value})


@underwriting_bp.route("/api/submit", methods=["POST"])
def submit_checklist():
    data = request.json or {}
    app_no = data.get("app_no", "OS121345678")
    uw_decision = data.get("uw_decision", "Accept")
    uw_remarks = data.get("uw_remarks", "")
    performed_by = data.get("performed_by", "UW_AGENT_01")

    state = crud.load_state(app_no)
    is_complete = service.update_completion_status(state)

    if not is_complete:
        incomplete = []
        for card_key in ["card2", "card3"]:
            for sec_key, sec in state["cards"][card_key].get("sections", {}).items():
                if not sec.get("completed", False) and not sec.get(
                    "auto_validated", False
                ):
                    incomplete.append(sec.get("title", sec_key))
        return jsonify(
            {
                "status": "incomplete",
                "message": f"{len(incomplete)} section(s) still pending",
                "incomplete_sections": incomplete,
            }
        ), 422

    sub_id = state.get("_submission_id")
    if not sub_id:
        return jsonify(
            {"status": "error", "message": "No active submission found"}
        ), 400

    crud.complete_submission(
        submission_id=sub_id,
        app_no=app_no,
        uw_decision=uw_decision,
        uw_remarks=uw_remarks,
        performed_by=performed_by,
    )

    decision_to_status = {
        "Accept": "Completed",
        "Refer": "Referred to Risk",
        "Reject": "Rejected",
    }
    new_status = decision_to_status.get(uw_decision, "Completed")

    return jsonify(
        {
            "status": "ok",
            "message": f"Checklist submitted. Case status updated to '{new_status}'.",
            "app_no": app_no,
            "new_case_status": new_status,
            "uw_decision": uw_decision,
            "submission_id": sub_id,
        }
    )


@underwriting_bp.route("/api/submit/force", methods=["POST"])
def force_submit():
    data = request.json or {}
    app_no = data.get("app_no", "OS121345678")
    uw_decision = data.get("uw_decision", "Accept")
    uw_remarks = data.get("uw_remarks", "Processed by automation agent")
    performed_by = data.get("performed_by", "AUTOMATION")

    state = crud.load_state(app_no)
    service.update_completion_status(state)
    crud.save_state(state)

    sub_id = state.get("_submission_id")
    if sub_id:
        crud.complete_submission(sub_id, app_no, uw_decision, uw_remarks, performed_by)

    decision_to_status = {
        "Accept": "Completed",
        "Refer": "Referred to Risk",
        "Reject": "Rejected",
    }
    return jsonify(
        {
            "status": "ok",
            "new_case_status": decision_to_status.get(uw_decision, "Completed"),
        }
    )


@underwriting_bp.route("/api/history/<app_no>")
def get_history(app_no):
    return jsonify(crud.get_history(app_no))


@underwriting_bp.route("/api/audit/<app_no>")
def get_audit(app_no):
    return jsonify(crud.get_audit(app_no))
