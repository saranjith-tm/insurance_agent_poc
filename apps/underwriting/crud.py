import database as db


def load_state(app_no: str) -> dict:
    return db.get_or_create_submission(app_no)


def save_state(state: dict):
    sub_id = state.get("_submission_id")
    if sub_id:
        db.save_submission_state(sub_id, state)


def reset_submission(app_no: str):
    with db.get_db() as conn:
        conn.execute(
            "UPDATE checklist_submissions SET submission_status = 'Cancelled' WHERE app_no = ? AND submission_status = 'In Progress'",
            (app_no,),
        )


def log_field_update(app_no, element_id, old_val, new_val):
    db.log_field_update(app_no, element_id, old_val, new_val)


def complete_submission(submission_id, app_no, uw_decision, uw_remarks, performed_by):
    db.complete_submission(submission_id, app_no, uw_decision, uw_remarks, performed_by)


def get_history(app_no):
    return db.get_submission_history(app_no)


def get_audit(app_no):
    return db.get_audit_log(app_no)


def get_case(app_no):
    return db.get_case(app_no)
