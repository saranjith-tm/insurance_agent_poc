"""
Audit-log database operations for the Insurance Underwriting POC.
"""

from __future__ import annotations
from .connection import get_db

def get_audit_log(app_no: str) -> list[dict]:
    """Return audit log entries for an application."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE app_no = ? ORDER BY timestamp DESC",
            (app_no,),
        ).fetchall()
        return [dict(r) for r in rows]

def log_field_update(
    app_no: str,
    field_name: str,
    old_value: str,
    new_value: str,
    performed_by: str = "UW_AGENT_01",
):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO audit_log (app_no, action, field_name, old_value, new_value, performed_by)
               VALUES (?, 'checklist_field', ?, ?, ?, ?)""",
            (app_no, field_name, str(old_value), str(new_value), performed_by),
        )
