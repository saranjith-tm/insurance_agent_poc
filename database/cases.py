"""
Case-related database operations for the Insurance Underwriting POC.
"""

from __future__ import annotations
from .connection import get_db

def get_all_cases() -> list[dict]:
    """Return all cases ordered by updated_at DESC."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

def get_case(app_no: str) -> dict | None:
    """Return a single case by application number."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cases WHERE app_no = ?", (app_no,)).fetchone()
        return dict(row) if row else None

def update_case_status(
    app_no: str,
    status: str,
    uw_status: str = None,
    uw_decision: str = None,
    uw_remarks: str = None,
    performed_by: str = "UW_AGENT_01",
):
    """Update a case's processing status and write an audit log entry."""
    with get_db() as conn:
        # Fetch current status for audit log
        row = conn.execute(
            "SELECT status, uw_status FROM cases WHERE app_no = ?", (app_no,)
        ).fetchone()
        old_status = row["status"] if row else None

        # Build update
        fields = ["status = ?", "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"]
        values: list = [status]

        if uw_status is not None:
            fields.append("uw_status = ?")
            values.append(uw_status)
        if uw_decision is not None:
            fields.append("uw_decision = ?")
            values.append(uw_decision)
        if uw_remarks is not None:
            fields.append("uw_remarks = ?")
            values.append(uw_remarks)

        values.append(app_no)
        conn.execute(f"UPDATE cases SET {', '.join(fields)} WHERE app_no = ?", values)

        # Write audit log
        conn.execute(
            """INSERT INTO audit_log (app_no, action, field_name, old_value, new_value, performed_by)
               VALUES (?, 'status_change', 'status', ?, ?, ?)""",
            (app_no, old_status, status, performed_by),
        )

def reset_all_cases_to_pending():
    """Reset all cases to Pending status and clear UW fields."""
    with get_db() as conn:
        conn.execute(
            """UPDATE cases
               SET status = 'Pending',
                   uw_status = NULL,
                   uw_decision = NULL,
                   uw_remarks = NULL,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"""
        )
