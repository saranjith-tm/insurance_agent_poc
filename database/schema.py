"""
Database schema definitions for the Insurance Underwriting POC.
"""

DDL = """
CREATE TABLE IF NOT EXISTS cases (
    app_no              TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    first_name          TEXT,
    last_name           TEXT,
    dob                 TEXT,
    age                 INTEGER,
    gender              TEXT,
    marital_status      TEXT,
    nationality         TEXT,
    resident_status     TEXT,
    pan_no              TEXT,
    aadhaar_no          TEXT,
    mobile              TEXT,
    email               TEXT,
    address1            TEXT,
    address2            TEXT,
    city                TEXT,
    state               TEXT,
    pincode             TEXT,
    country             TEXT,
    occupation          TEXT,
    organisation_type   TEXT,
    industry            TEXT,
    education           TEXT,
    annual_income       REAL,
    experian_income     REAL,
    politically_exposed TEXT,
    high_risk           TEXT,
    bank_account        TEXT,
    bank_name           TEXT,
    ifsc                TEXT,
    nominee_name        TEXT,
    nominee_relation    TEXT,
    plan                TEXT,
    product_code        TEXT,
    sum_assured         REAL,
    premium             REAL,
    sourcing_type       TEXT,
    advisor_code        TEXT,
    -- Queue-level fields
    holding_type        TEXT,
    sro                 TEXT DEFAULT '<2 Hours',
    case_type           TEXT,
    tsa                 REAL,
    audit_flag          TEXT DEFAULT '',
    -- Status fields
    status              TEXT NOT NULL DEFAULT 'Pending',
    uw_status           TEXT,          -- NULL / 'In Progress' / 'Completed' / 'Referred to Risk'
    uw_decision         TEXT,          -- 'Accept' / 'Reject' / 'Refer'
    uw_remarks          TEXT,
    -- Timestamps
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS checklist_submissions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    app_no              TEXT NOT NULL REFERENCES cases(app_no),
    state_json          TEXT NOT NULL,          -- Full checklist JSON snapshot
    submission_status   TEXT NOT NULL DEFAULT 'In Progress',  -- 'In Progress' / 'Completed'
    processed_by        TEXT DEFAULT 'UW_AGENT_01',
    started_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at        TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    app_no          TEXT NOT NULL,
    action          TEXT NOT NULL,    -- 'status_change' / 'checklist_field' / 'checklist_complete' / 'case_opened'
    field_name      TEXT,
    old_value       TEXT,
    new_value       TEXT,
    performed_by    TEXT DEFAULT 'UW_AGENT_01',
    timestamp       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_checklist_app_no ON checklist_submissions(app_no);
CREATE INDEX IF NOT EXISTS idx_audit_app_no ON audit_log(app_no);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
"""
