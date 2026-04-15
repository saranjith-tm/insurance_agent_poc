"""
Submission-related database operations for the Insurance Underwriting POC.
"""

from __future__ import annotations
import json
import copy
from datetime import datetime, timezone
from .connection import get_db

def get_or_create_submission(app_no: str) -> dict:
    """
    Return the active (In Progress) submission for app_no, or create a new one
    with DEFAULT_STATE from the underwriting app.
    """
    from apps.underwriting.constants import DEFAULT_STATE

    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM checklist_submissions
               WHERE app_no = ? AND submission_status = 'In Progress'
               ORDER BY started_at DESC LIMIT 1""",
            (app_no,),
        ).fetchone()

        if row:
            state = json.loads(row["state_json"])
            state["_submission_id"] = row["id"]
            # Ensure new fields/sections are present in legacy database records
            reconcile_state(state, DEFAULT_STATE)
            return state

        # Create new submission
        fresh = copy.deepcopy(DEFAULT_STATE)
        fresh["application_no"] = app_no

        cur = conn.execute(
            """INSERT INTO checklist_submissions (app_no, state_json, submission_status)
               VALUES (?, ?, 'In Progress')""",
            (app_no, json.dumps(fresh)),
        )
        fresh["_submission_id"] = cur.lastrowid

        # Mark case as In Progress
        conn.execute(
            """UPDATE cases SET status = 'In Progress',
               uw_status = 'In Progress',
               updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE app_no = ? AND status = 'Pending'""",
            (app_no,),
        )
        conn.execute(
            """INSERT INTO audit_log (app_no, action, field_name, old_value, new_value)
               VALUES (?, 'status_change', 'status', 'Pending', 'In Progress')""",
            (app_no,),
        )
        return fresh

def save_submission_state(submission_id: int, state: dict):
    """Persist updated checklist state JSON for an existing submission."""
    payload = {k: v for k, v in state.items() if k != "_submission_id"}
    with get_db() as conn:
        conn.execute(
            "UPDATE checklist_submissions SET state_json = ? WHERE id = ?",
            (json.dumps(payload), submission_id),
        )

def complete_submission(
    submission_id: int,
    app_no: str,
    uw_decision: str = "Accept",
    uw_remarks: str = "",
    performed_by: str = "UW_AGENT_01",
):
    """
    Mark a checklist submission as Completed and update the parent case status.
    This is the key function that bridges checklist → case status.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        conn.execute(
            """UPDATE checklist_submissions
               SET submission_status = 'Completed', completed_at = ?
               WHERE id = ?""",
            (now, submission_id),
        )

        # Map decision to case status
        decision_to_status = {
            "Accept": "Completed",
            "Refer": "Referred to Risk",
            "Reject": "Rejected",
        }
        new_status = decision_to_status.get(uw_decision, "Completed")

        old_row = conn.execute(
            "SELECT status FROM cases WHERE app_no = ?", (app_no,)
        ).fetchone()
        old_status = old_row["status"] if old_row else "In Progress"

        conn.execute(
            """UPDATE cases
               SET status = ?, uw_status = 'Completed', uw_decision = ?,
                   uw_remarks = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE app_no = ?""",
            (new_status, uw_decision, uw_remarks, app_no),
        )

        conn.execute(
            """INSERT INTO audit_log (app_no, action, field_name, old_value, new_value, performed_by)
               VALUES (?, 'checklist_complete', 'status', ?, ?, ?)""",
            (app_no, old_status, new_status, performed_by),
        )

def get_submission_history(app_no: str) -> list[dict]:
    """Return all past submissions for an application."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, submission_status, processed_by, started_at, completed_at, notes
               FROM checklist_submissions WHERE app_no = ?
               ORDER BY started_at DESC""",
            (app_no,),
        ).fetchall()
        return [dict(r) for r in rows]

def reconcile_state(state: dict, default_state: dict):
    """Recursively merge missing keys from default_state into state."""
    for key, value in default_state.items():
        if key not in state:
            state[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(state[key], dict):
            reconcile_state(state[key], value)
