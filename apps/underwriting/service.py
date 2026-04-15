import copy
from apps.underwriting.constants import DEFAULT_STATE


def get_path_value(state: dict, path: list):
    obj = state
    for key in path:
        obj = obj[key]
    return obj


def set_path_value(state: dict, path: list, value):
    obj = state
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def update_completion_status(state: dict):
    c2 = state["cards"]["card2"]["sections"]
    completed = 0
    for section in c2.values():
        fields = section.get("fields", {})
        none_fields = [v for v in fields.values() if v is None]
        if len(none_fields) == 0 and any(v is not None for v in fields.values()):
            section["completed"] = True
            completed += 1

    state["cards"]["card2"]["sections_completed"] = completed
    state["cards"]["card2"]["total_sections"] = len(c2)

    c3 = state["cards"]["card3"]["sections"]
    occ = c3["occupation"]["fields"]
    if occ["occupation"] and occ["industry_type"] and occ["is_hazardous"] is not None:
        c3["occupation"]["completed"] = True

    if c3["education"]["fields"]["education_level"]:
        c3["education"]["completed"] = True

    if c3["nominee"]["fields"]["nominee_details_added"] is not None:
        c3["nominee"]["completed"] = True

    all_c2 = all(s.get("completed", False) for s in c2.values())
    all_c3 = all(s.get("completed", False) for s in c3.values())
    overall = all_c2 and all_c3
    state["cards"]["card2"]["completed"] = all_c2
    state["cards"]["card3"]["completed"] = all_c3
    return overall


def generate_fresh_state(app_no):
    fresh = copy.deepcopy(DEFAULT_STATE)
    fresh["application_no"] = app_no
    return fresh
