"""
Database Layer for the Insurance Underwriting POC.
Consolidates connection management, initialization, and domain CRUD operations.
"""

from __future__ import annotations

# Re-export connection management
from .connection import get_db

# Re-export initialization
from .seeders import init_db

# Re-export CRUD domain operations
from .cases import (
    get_all_cases,
    get_case,
    update_case_status,
    reset_all_cases_to_pending,
)
from .submissions import (
    get_or_create_submission,
    save_submission_state,
    complete_submission,
    get_submission_history,
)
from .audit import (
    get_audit_log,
    log_field_update,
)
