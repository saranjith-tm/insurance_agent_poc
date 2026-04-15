import database as db


def get_all_cases():
    return db.get_all_cases()


def get_case(app_no):
    return db.get_case(app_no)


def get_audit_log(app_no):
    return db.get_audit_log(app_no)


def get_submission_history(app_no):
    return db.get_submission_history(app_no)
