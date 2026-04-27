# Insurance Underwriting Automation POC — CLAUDE.md

This document is the **authoritative technical reference** for AI coding assistants and developers working on this project. Read it fully before making any changes.

---

## 🏗️ System Architecture

The project is built on an **n-tier modular architecture** with four distinct zones:

| Zone | Directory | Purpose |
|------|-----------|---------|
| **Simulated Environment** | `apps/` | Two Flask web apps — Sales Agent portal & Underwriter Checklist |
| **Intelligence Layer** | `intelligence/` | Core automation brain: Playwright browser control + VLM visual reasoning |
| **Orchestration Dashboard** | `dashboard/` | Streamlit UI for model config, run control, and live log monitoring |
| **Data Layer** | `database/` | SQLite persistence for case records, checklist submissions, and audit logs |

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|-----------|
| **Automation Engine** | Playwright (Python, sync API) |
| **Visual Intelligence** | Qwen2.5-VL (7B / 32B / 72B via OpenRouter), Claude 3.5 Sonnet (Anthropic), GPT-4o (OpenAI), Gemini 1.5 Pro (Google) |
| **Web Apps** | Flask 2.3+ (Sales Agent + Underwriting), Streamlit 1.28+ (Dashboard) |
| **Frontend** | HTML5, Vanilla CSS, PDF.js (for multi-page document rendering in `doc_viewer.html`) |
| **Database** | SQLite (via Python `sqlite3`) |
| **HTTP Client** | `httpx` (sync, used inside agent for inter-service REST calls) |
| **Image Handling** | Pillow (`PIL`) |
| **Config** | `python-dotenv` (`.env` file), centralized `config.py` |

---

## 📁 Complete Project Structure

```text
insurance_poc/
│
├── apps/                               # Simulated Insurance Environment
│   ├── __init__.py
│   ├── sales_agent/                    # Case queue & document viewer portal
│   │   ├── app.py                      # Flask app factory (port 5001)
│   │   ├── router.py                   # URL routes: /, /case/<id>, /case/<id>/single, /case/<id>/docs, /api/applicant/<id>
│   │   ├── service.py                  # Business logic for case & document retrieval
│   │   ├── crud.py                     # DB reads for applicant data
│   │   ├── static/                     # CSS, JS assets
│   │   └── templates/
│   │       └── doc_viewer.html         # PDF.js multi-page canvas renderer
│   │
│   └── underwriting/                   # Target checklist application for automation
│       ├── app.py                      # Flask app factory (port 5002)
│       ├── router.py                   # URL routes: /<app_no>, /api/fill, /api/click, /api/submit, /api/submit/force
│       ├── service.py                  # Checklist fill logic & validation
│       ├── crud.py                     # DB reads/writes for checklist state
│       ├── constants.py                # Checklist field definitions, section IDs, dropdown option maps
│       ├── static/
│       └── templates/
│           └── checklist.html          # Card-based checklist UI (Card 1, Card 2 KYC, Card 3 Financial)
│
├── intelligence/                       # The AI Automation Brain
│   ├── __init__.py
│   ├── agent.py                        # UnderwritingAgent class + run_automation_in_thread()
│   ├── helpers.py                      # AutomationState class + get_vlm_client() factory
│   ├── playwright_helper.py            # PlaywrightHelper class (UI actions, REST fills, screenshots)
│   │
│   ├── tools/                          # Modular automation step handlers
│   │   ├── __init__.py
│   │   ├── navigation.py               # Step 1 & 4: navigate_to_sales_agent, navigate_to_documents
│   │   ├── extraction.py               # Step 2: extract applicant data (API-first, VLM fallback)
│   │   ├── verification.py             # Step 3: VLM-based document tab discovery & validation
│   │   ├── bank_statement.py           # Step 5: multi-page scrolling & minimum balance extraction
│   │   ├── checklist.py                # Step 6: Master Fill orchestrator (calls fill.py functions)
│   │   ├── fill.py                     # All granular fill functions (KYC, PAN, Aadhaar, Bank, etc.)
│   │   └── submit.py                   # Step 7: REST API checklist submission + force-submit fallback
│   │
│   └── vlm_clients/                    # Pluggable VLM provider clients
│       ├── __init__.py
│       ├── base.py                     # VLMBase abstract class + VLMAction dataclass
│       ├── openrouter_client.py        # OpenRouter (Qwen, Pixtral) — primary provider
│       ├── anthropic_client.py         # Claude 3.5 Sonnet via Anthropic SDK
│       ├── openai_client.py            # GPT-4o via OpenAI SDK
│       └── google_client.py            # Gemini 1.5 Pro via google-generativeai
│
├── dashboard/                          # Orchestration Interface (Streamlit)
│   ├── app.py                          # Main Streamlit UI (config panel, run controls, live monitor)
│   ├── constants.py                    # Dashboard string constants and defaults
│   ├── service.py                      # Dashboard business logic (start/stop automation)
│   ├── crud.py                         # Dashboard DB helpers (fetch case status)
│   └── ui_components.py               # Custom CSS, HTML metric cards, log formatters
│
├── database/                           # SQLite Persistence Layer
│   ├── __init__.py                     # DB initializer: creates tables if not exists
│   ├── connection.py                   # get_connection() — returns sqlite3.Connection
│   ├── schema.py                       # DDL: cases, checklist_submissions, audit_log tables
│   ├── cases.py                        # CRUD ops for the cases table
│   ├── submissions.py                  # CRUD ops for checklist_submissions table
│   ├── audit.py                        # CRUD ops for audit_log table
│   ├── seeders.py                      # Seed script: populates dummy applicant data & documents
│   └── data/                           # SQLite DB file stored here at runtime
│
├── config.py                           # Centralized config: ports, URLs, VLM model catalog, APPLICANT_DATA
├── run.py                              # Master process launcher (starts all 3 services as subprocesses)
├── requirements.txt                    # Python dependencies
├── .env                                # Secret API keys (never committed)
└── .gitignore
```

---

## ⚙️ Configuration (`config.py`)

All ports, URLs, and model options are defined here. **Never hardcode these elsewhere.**

```python
SALES_AGENT_PORT   = 5001
UNDERWRITING_PORT  = 5002
DASHBOARD_PORT     = 8501

SALES_AGENT_URL    = "http://localhost:5001"
UNDERWRITING_URL   = "http://localhost:5002"
```

### Available VLM Models (`VLM_MODELS` dict)

| Key (Display Name) | Provider | Model ID |
|---|---|---|
| OpenRouter - Qwen2.5-VL-32B (Recommended) | `openrouter` | `qwen/qwen2.5-vl-32b-instruct` |
| OpenRouter - Qwen2.5-VL-72B | `openrouter` | `qwen/qwen2.5-vl-72b-instruct` |
| OpenRouter - Qwen2.5-VL-7B (Fast) | `openrouter` | `qwen/qwen2.5-vl-7b-instruct` |
| OpenRouter - Pixtral 12B (Free) | `openrouter` | `mistralai/pixtral-12b` |
| Anthropic - Claude 3.5 Sonnet | `anthropic` | `claude-3-5-sonnet-20241022` |
| OpenAI - GPT-4o | `openai` | `gpt-4o` |
| Google - Gemini 1.5 Pro | `google` | `gemini-1.5-pro` |

---

## 🔄 Core Automation Loop — Step-by-Step

The agent follows a strict **Discovery-First, Single-Pass-Fill** strategy. Steps execute sequentially in `agent.py`.

```
agent.run()
  │
  ├─ 1. navigation.run_step_navigate_to_sales_agent()     [progress: 0.02]
  │      → loads /case/{app_no}, takes screenshot
  │
  ├─ 2. extraction.run_step_extract_single_screen_data()  [progress: 0.08]
  │      → GET /api/applicant/{app_no} (API-first)
  │      → Falls back to VLM screenshot extraction
  │      → Populates agent._applicant_data dict
  │
  ├─ 3. navigation.run_step_navigate_to_documents()       [progress: 0.35]
  │      → loads /case/{app_no}/docs
  │
  ├─ 4. verification.run_step_verify_documents()          [progress: 0.55]
  │      → Loops through document tabs: [PhotoIDProof, Others, NonMedicalDeclar, FaceVerificationRep, RCR]
  │      → VLM classifies each tab (PAN / Aadhaar / Bank / RCR / Other)
  │      → VLM validates legibility and ID number match
  │      → Populates agent._document_validation dict
  │
  ├─ 5. bank_statement.run_step_extract_min_balance()     [progress: 0.75]
  │      → Re-checks same tabs looking for bank statement
  │      → Scrolls multi-page PDF up to 5 pages per tab
  │      → VLM extracts minimum_balance from Balance column
  │      → Stores in agent._applicant_data["minimum_balance"]
  │
  ├─ 6. checklist.run_step_final_checklist_update()       [progress: 0.90]
  │      → "Master Fill" — navigates to UW app ONCE
  │      → fill_initial_case_details()      → Card 1 (app_no, case_type, sourcing, gender)
  │      → update_checklist_with_verification_results() → Card 2 KYC (PAN, Aadhaar, Address, Photo, Bank)
  │      → fill_financial_sections()        → Card 3 (Occupation, Min Balance, Education, Nominee)
  │
  └─ 7. submit.run_step_submit()                          [progress: 0.98]
         → POST /api/submit  →  uw_decision="Accept"
         → Fallback: POST /api/submit/force  (if 422 incomplete sections)
         → Reloads page for final screenshot
```

### Key Agent State Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent._applicant_data` | `dict` | Extracted applicant info from Sales Agent API |
| `agent._document_validation` | `dict` | VLM verification results per document type |
| `agent._applicant_data["minimum_balance"]` | `str` | Extracted min balance (or "Not Found" / "Error") |
| `agent.state` | `AutomationState` | Shared thread-safe state for dashboard communication |
| `agent.ui` | `PlaywrightHelper` | All browser interaction methods |
| `agent.vlm` | `VLMBase` subclass | Active VLM provider client |

---

## 🧩 Intelligence Layer — Key Classes & Functions

### `AutomationState` (`intelligence/helpers.py`)
Thread-safe shared state between automation thread and Streamlit dashboard.

| Field | Type | Purpose |
|-------|------|---------|
| `running` | bool | Whether automation is active |
| `completed` | bool | Whether run finished successfully |
| `error` | str | Last error message if any |
| `progress` | float | 0.0–1.0 progress value |
| `current_step` | str | Human-readable current step label |
| `log_entries` | list[dict] | All log messages with timestamp + level |
| `screenshots` | list[tuple] | (label, base64_png) tuples, max 20 |
| `latest_screenshot_b64` | str | Most recent screenshot for live view |
| `video_path` | str \| None | Path to WebM recording if enabled |
| `extracted_data` | dict | Copy of `_applicant_data` for display |

Key methods: `log(message, level)`, `add_screenshot(label, bytes)`, `set_step(step, section)`, `set_progress(float)`, `reset()`

---

### `PlaywrightHelper` (`intelligence/playwright_helper.py`)
Wraps all Playwright interactions. Every fill action auto-scrolls and takes a live screenshot.

| Method | Description |
|--------|-------------|
| `click_yn(field_id, is_yes, label)` | Clicks `#btn_{field_id}_yes` or `#btn_{field_id}_no`. Auto-scrolls and updates live view. |
| `fill_text(input_id, value, label)` | Types into `#{input_id}`, dispatches `change` event. |
| `select(input_id, value, label)` | `page.select_option(#{input_id})` then dispatches `change`. |
| `scroll_to(element_id)` | Smooth-scrolls `element_id` into center view. |
| `api_fill(field_id, value, label)` | POST `/api/fill` — fast REST-only fill (no browser interaction). |
| `api_click(field_id, value, label)` | POST `/api/click` — fast REST-only click. |
| `screenshot()` | Takes PNG screenshot, updates `state.latest_screenshot_b64`. Returns bytes. |
| `wait(seconds)` | `time.sleep(seconds)`, defaults to `step_delay`. |

> **Critical**: Always call `self.screenshot()` after actions to feed the dashboard live view.

---

### `get_vlm_client(model_config, api_key)` (`intelligence/helpers.py`)
Factory function — returns the correct VLM client based on `provider`:

- `"openrouter"` → `OpenRouterClient`
- `"anthropic"` → `AnthropicClient`
- `"openai"` → `OpenAIVLMClient`
- `"google"` → `GoogleVLMClient`

---

## 📋 VLM Clients (`intelligence/vlm_clients/`)

All clients implement the same interface from `base.py`:

```python
class VLMBase:
    def analyze_document(self, screenshot: bytes, prompt: str) -> dict
    def extract_data(self, screenshot: bytes, fields: list[str]) -> dict
```

`analyze_document()` always returns a **parsed dict** (never raw string). On JSON parse failure it returns `{"parsing_error": True, "raw_response": "..."}`.

### VLM Prompt Contract (verification + bank_statement)
Both `verification.py` and `bank_statement.py` send structured JSON-returning prompts to the VLM. The agent treats any response with `parsing_error=True` as a warning (non-fatal) and continues.

---

## 📋 Document Validation (`agent._document_validation`)

Structure set by `verification.py`:

```python
{
    "pan_valid": bool,
    "aadhaar_valid": bool,
    "bank_statement_valid": bool,
    "proposal_valid": bool,
    "validation_details": {
        "PhotoIDProof": {"doc_type": "PAN", "valid": True, "reasoning": "..."},
        "Others":       {"doc_type": "AADHAAR", "valid": True, "reasoning": "..."},
        # ...one entry per tab checked
    }
}
```

These values directly drive the Yes/No clicks in `fill.py` (see `update_checklist_with_verification_results()`).

---

## 🗄️ Database Schema (`database/schema.py`)

Three tables:

### `cases` (primary applicant record)
- **PK**: `app_no` (e.g. `"OS121345678"`)
- Key fields: `name`, `pan_no`, `aadhaar_no`, `dob`, `gender`, `occupation`, `industry`, `education`, `annual_income`, `bank_account`, `ifsc`, `nominee_name`, `nominee_relation`, `resident_status`, `sum_assured`, `premium`, `case_type`, `sourcing_type`
- Status fields: `status` (default `"Pending"`), `uw_status`, `uw_decision`, `uw_remarks`

### `checklist_submissions`
- **FK**: `app_no` → `cases`
- Stores the full checklist JSON snapshot (`state_json`) at each save
- `submission_status`: `"In Progress"` / `"Completed"`

### `audit_log`
- Tracks every field change: `action`, `field_name`, `old_value`, `new_value`, `performed_by`, `timestamp`

---

## 🌐 REST API Contracts

### Sales Agent App (port 5001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Case queue list |
| GET | `/case/<app_no>` | Case overview page |
| GET | `/case/<app_no>/single` | Single-screen applicant summary |
| GET | `/case/<app_no>/docs` | Document viewer (PDF.js) |
| GET | `/api/applicant/<app_no>` | **JSON** — returns full applicant dict |

### Underwriting App (port 5002)

| Method | Endpoint | Payload | Description |
|--------|----------|---------|-------------|
| GET | `/<app_no>` | — | Checklist form page |
| POST | `/api/fill` | `{element_id, value, app_no}` | Fill a text/select field |
| POST | `/api/click` | `{element_id, value, app_no}` | Click a Yes/No button |
| POST | `/api/submit` | `{app_no, uw_decision, uw_remarks, performed_by}` | Submit checklist (422 if incomplete) |
| POST | `/api/submit/force` | same as above | Force-submit bypassing validation |

---

## 🏃 Running the Project

### Start Everything
```bash
python run.py
```
Opens dashboard at `http://localhost:8501` automatically.

### Selective Start
```bash
python run.py --sales      # Sales Agent only (port 5001)
python run.py --uw         # Underwriting App only (port 5002)
python run.py --dashboard  # Dashboard only (port 8501)
python run.py --no-browser # Don't auto-open browser
```

### Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Environment Setup
Create a `.env` file in the project root:
```
OPENROUTER_API_KEY=sk-or-...
# Optional overrides:
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

---

## 👤 Dummy Applicant Data (`config.py → APPLICANT_DATA`)

The seeded test case used for all automation runs:

| Field | Value |
|-------|-------|
| `application_no` | `OS121345678` |
| `name` | Kailash Suresh |
| `pan_no` | `ABCKS1234K` |
| `aadhaar_no` | `1234 5678 9012` |
| `dob` | `15/03/1985` |
| `gender` | Male |
| `resident_status` | NRI |
| `occupation` | Salaried |
| `industry` | IT/Software |
| `education` | Graduate |
| `annual_income` | ₹60,00,000 |
| `bank_account` | `12345678901234` |
| `bank_name` | HDFC Bank |
| `ifsc` | `HDFC0001234` |
| `nominee_name` | Priya Suresh |
| `nominee_relation` | Wife |
| `plan` | UW3 - Term Life Insurance |
| `sum_assured` | ₹45,00,000 |
| `premium` | ₹50,000 |

---

## 🎬 Browser & Video Recording

- **Viewport**: 1280 × 900 (fixed in `agent.py`)
- **Mode**: Headless by default; `headed=True` launches visible Chrome (falls back to headless if no display)
- **Video**: Set `record_video=True` → saves WebM to `recordings/` directory
- **Video path**: Accessible via `agent.state.video_path` after run completes

---

## 💡 Key Implementation Notes for AI Tools

### Fill Mechanism
- **Playwright fills** (`click_yn`, `fill_text`, `select`) are used for all Master Fill steps — they are **visible** in the browser/recording and trigger `onchange` → `/api/fill` REST call automatically.
- **REST-only fills** (`api_fill`, `api_click`) are a fast-path alternative that bypasses browser interaction — only use when silent background updates are acceptable.

### PDF Rendering
- Multi-page PDFs are rendered as a **vertical stack of `<canvas>` elements** via PDF.js in `doc_viewer.html`.
- The VLM "sees" each page by scrolling the `#docPanel` div. The `bank_statement.py` tool scrolls `clientHeight * 0.8` per step (up to 5 pages).
- Wait `4.5s` after clicking a document tab before screenshotting (PDF.js render time).

### Document Tab Discovery
Tabs checked in order: `["PhotoIDProof", "Others", "NonMedicalDeclar", "FaceVerificationRep", "RCR"]`
- `NonMedicalDeclar` and `RCR` are **trusted** bank statement tabs (forced identification even on VLM parse errors).

### Dropdown Value Maps (`fill.py`)
- Occupation: `{Salaried, Self Employed, Business, Professional, Retired, Homemaker}`
- Industry: `{IT/Software, Banking/Finance, Healthcare, Manufacturing, Agriculture, Retail, Government}`
- Hazardous industries (auto-flag `is_hazardous=True`): `{Mining, Oil & Gas, Explosives, Defence, Fishing}`
- Education: `{Graduate, Post Graduate, HSC / 12th, SSC / 10th, Other}` with aliases (e.g. `GRAD` → `Graduate`)
- Resident Status: `{NRI, Resident Indian, PIO, Foreign National}`

### Aadhaar Masking
Aadhaar is stored and displayed as `XXXX XXXX XXXX` — first 8 digits masked per UIDAI guidelines before entering into the checklist.

### Resilience Patterns
- All navigation steps use `page.wait_for_load_state("domcontentloaded", timeout=15000)`.
- VLM failures (JSON parse errors) are **non-fatal warnings** — the agent continues with defaults.
- Submit step auto-falls back to `/api/submit/force` on HTTP 422.
- Document validation failures default to `pan_valid=True` / `aadhaar_valid=True` to avoid blocking the run.

### Thread Safety
`AutomationState` uses a `threading.Lock` (`_lock`) for all writes. The agent runs in a daemon thread via `run_automation_in_thread()`. Never write to `state` fields directly without the lock (use the provided methods).

### Dashboard Live View
`state.latest_screenshot_b64` holds the most recent base64-PNG. The Streamlit dashboard polls this to render the "Live Browser View" panel. Always call `self.ui.screenshot()` after UI actions to keep this fresh.

---

## 🚧 Architecture Decisions & Gotchas

1. **Single Navigate to UW App** — The "Master Fill" (`checklist.py`) navigates to the underwriting app only **once** and fills all cards in one continuous pass. Do NOT add additional `page.goto()` calls to the UW app in between fill functions.

2. **API-First Data Extraction** — `extraction.py` always tries the Sales Agent REST API (`/api/applicant/{app_no}`) before using VLM screenshot extraction. Only fall back to VLM if the API fails.

3. **`fill.py` vs `checklist.py`** — `checklist.py` is the **orchestrator** (high-level step runner), `fill.py` contains all the granular fill logic. New checklist sections should be added as functions in `fill.py` and called from `checklist.py`.

4. **`constants.py` in underwriting app** — All checklist field IDs, section anchor IDs, and dropdown option arrays are defined here. Always check `constants.py` before adding or modifying field interactions.

5. **No VLM for Checklist Filling** — The Master Fill uses pure Playwright + REST (not VLM) to fill the checklist. VLM is only used for document analysis in the Sales Agent app.
