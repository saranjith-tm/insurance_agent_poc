# 🤖 Intelligence Folder — Full Workflow Walkthrough

> **Written for Node.js developers with no AI agent experience.**
> Think of this agent like an automated browser bot that can also **see and understand screenshots** using a powerful AI model (like GPT-4 or Claude).

---

## 📦 What Is the `intelligence` Folder?

This folder is the **brain** of your insurance automation system. It contains:

- The **main agent** that drives the whole process
- **Tools** (functions that do specific jobs, like navigating or filling forms)
- **VLM clients** (connectors to AI vision models like Claude, GPT-4, Gemini)
- **Helpers** (utility classes for tracking state and creating AI clients)

> **Node.js analogy:** Think of this like a well-structured Express.js project, where `agent.py` = your `app.js` (entry point), `tools/` = your `routes/`, and `vlm_clients/` = your `services/` or API integrations.

---

## 🗂️ File Structure

```
intelligence/
│
├── agent.py              ← 🟢 MAIN ENTRY POINT — The orchestrator
├── helpers.py            ← 🔧 AutomationState class + VLM factory
├── playwright_helper.py  ← 🖱️ Browser control helper (click, type, screenshot)
│
├── tools/                ← 🛠️ Each file = one "job" the agent can do
│   ├── navigation.py     ← Step 1 & 4: Open URLs in browser
│   ├── extraction.py     ← Step 2: Read applicant data from the screen
│   ├── verification.py   ← Step 3: Verify documents (PAN, Aadhaar, etc.)
│   ├── bank_statement.py ← Step 5: Find the minimum bank balance
│   ├── checklist.py      ← Step 6: Fill the underwriting checklist form
│   ├── fill.py           ← Helper functions used by checklist.py
│   └── submit.py         ← Step 7: Submit the completed form
│
└── vlm_clients/          ← 🤖 AI Model connectors
    ├── base.py           ← Abstract base class (like an interface in TypeScript)
    ├── openrouter_client.py  ← OpenRouter API (default)
    ├── anthropic_client.py   ← Claude (Anthropic) API
    ├── openai_client.py      ← OpenAI (GPT-4o) API
    └── google_client.py      ← Gemini API
```

---

## 🧩 The 3 Key Concepts Before You Read The Steps

### 1. 🖥️ Playwright — "The Robot Hands"
[Playwright](https://playwright.dev/) is a browser automation library (same as Puppeteer in Node.js).
It lets the agent **open a real browser, navigate to pages, click buttons, fill forms, and take screenshots**.

> Node.js analogy: It's exactly like `puppeteer` or `playwright` in Node — same concept, just in Python.

### 2. 🤖 VLM (Vision Language Model) — "The Robot Eyes + Brain"
A VLM is an AI model (Claude, GPT-4o, Gemini) that can **look at a screenshot and understand what's in it**.
The agent sends a screenshot + a question to the AI, and it answers back in JSON.

**Example:**
```
Agent sends: [Screenshot of a PAN card] + "Is this PAN card valid? Does it match the applicant?"
AI responds: { "doc_type": "PAN", "valid": true, "confidence": 0.95, "reasoning": "PAN number matches records" }
```

### 3. 📋 AutomationState — "The Shared Memory"
`AutomationState` is a Python class (like a shared object/store) that holds **everything the agent knows**:
- What step it's on
- What data it extracted
- Screenshots it took
- Logs, errors, progress
- Token usage & costs

> Node.js analogy: It's like a `redux store` or a `singleton` object that both the agent and the dashboard can read.

---

## 🚀 Full Step-by-Step Workflow

When the agent runs, it goes through **7 sequential steps**. Here's what happens in each one:

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_automation_in_thread()                    │
│   (Starts agent in background thread, like a Node.js Worker)    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   agent.run()        │
                    │  (Launches browser)  │
                    └──────────┬──────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 1: navigate_to_sales_agent                             │
    │  📂 tools/navigation.py                                      │
    │  → Opens browser → Goes to Sales Agent App URL              │
    │  → Takes a screenshot for the dashboard                      │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 2: extract_single_screen_data                          │
    │  📂 tools/extraction.py                                      │
    │  → Calls REST API first: /api/applicant/{app_no}            │
    │  → If API fails → sends screenshot to VLM (AI)              │
    │  → AI reads the screen and extracts: name, PAN, Aadhaar,    │
    │    DOB, income, bank account, etc.                           │
    │  → Saves to agent._applicant_data {}                         │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 3: navigate_to_documents                               │
    │  📂 tools/navigation.py                                      │
    │  → Navigates browser to the Documents page                  │
    │  → Takes a screenshot                                        │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 4: verify_documents                                    │
    │  📂 tools/verification.py                                    │
    │  → Loops through document tabs: PhotoIDProof, Others, etc.  │
    │  → For each tab: clicks it, waits for PDF to render         │
    │  → Takes screenshot → sends to AI with this question:       │
    │    "What document is this? Is it valid? Extract any IDs."   │
    │  → AI responds with: doc_type, valid, confidence, data      │
    │  → Saves: pan_valid, aadhaar_valid, bank_statement_valid    │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 5: extract_min_balance                                 │
    │  📂 tools/bank_statement.py                                  │
    │  → Loops through document tabs again                        │
    │  → Asks AI: "Is this a bank statement? What's the          │
    │    LOWEST balance in the Balance column?"                    │
    │  → Scrolls down through multiple pages to check all         │
    │  → Saves minimum balance to agent._applicant_data           │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 6: final_checklist_update                              │
    │  📂 tools/checklist.py + tools/fill.py                      │
    │  → Navigates to Underwriting App                            │
    │  → Calls fill_initial_case_details() → fills Card 1         │
    │  → Calls update_checklist_with_verification_results()        │
    │    → fills Card 2 (KYC: PAN ✅/❌, Aadhaar ✅/❌, etc.)    │
    │  → Calls fill_financial_sections() → fills Card 3           │
    │    (Occupation, Income, Min Balance)                         │
    │  → Each field is filled by clicking via Playwright          │
    └──────────────────────────┬──────────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────────┐
    │  STEP 7: submit                                              │
    │  📂 tools/submit.py                                          │
    │  → Calls POST /api/submit on the Underwriting App           │
    │  → If 422 (incomplete) → calls /api/submit/force            │
    │  → Takes final screenshot to show "Completed" status        │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ✅ DONE!            │
                    │  state.completed=True│
                    └─────────────────────┘
```

---

## 📄 File-by-File Breakdown

### 🟢 `agent.py` — The Orchestrator (Like `app.js`)

This is the **main file**. It does two things:

1. **`UnderwritingAgent` class** — Contains `run()` which launches the browser (Playwright) and calls each tool step in order.
2. **`run_automation_in_thread()` function** — Called by the dashboard (Streamlit). Starts the agent in a **background thread** so the UI doesn't freeze.

```
Node.js analogy:
run_automation_in_thread() = new Worker('./agent.js')
UnderwritingAgent.run()    = The worker's code
```

**Key properties set in `__init__`:**
| Property | What It Is |
|---|---|
| `self.vlm` | The AI client (Claude/GPT-4o/Gemini) |
| `self.page` | The Playwright browser page |
| `self.ui` | PlaywrightHelper — browser control methods |
| `self.state` | AutomationState — shared memory/store |
| `self._applicant_data` | Dict holding all extracted applicant info |

---

### 🔧 `helpers.py` — The Factory + State Store

**`get_vlm_client()`** — A factory function. You pass it a config like `{ provider: "anthropic", model_id: "claude-3-5" }` and it returns the right AI client.

```python
# Node.js analogy — like a factory function:
function getAIClient(config) {
  if (config.provider === 'anthropic') return new AnthropicClient(config);
  if (config.provider === 'openai') return new OpenAIClient(config);
}
```

**`AutomationState`** — A class with properties that act as a **shared store** between the agent thread and the dashboard UI. The dashboard reads from it every few seconds to update what it shows.

Key fields:
| Field | Purpose |
|---|---|
| `running` | Is the agent currently active? |
| `progress` | 0.0 to 1.0 — shown as progress bar |
| `log_entries` | List of log messages shown in dashboard |
| `extracted_data` | What was read from the applicant screen |
| `screenshots` | List of screenshots taken during the run |
| `input_tokens / output_tokens` | Track AI usage |
| `total_cost` | Running cost of all AI calls |
| `doc_confidences` | Per-document confidence scores |

---

### 🖱️ `playwright_helper.py` — The Browser Remote Control

This class wraps all the Playwright actions into clean, named methods.

| Method | What It Does |
|---|---|
| `screenshot()` | Takes a PNG screenshot of the current page |
| `wait(seconds)` | Pauses for N seconds |
| `click_yn(field_id, True/False, label)` | Clicks a Yes or No button by its HTML ID |
| `fill_text(input_id, value, label)` | Types a value into a text input |
| `select(input_id, value, label)` | Selects a dropdown option |
| `scroll_to(element_id)` | Smoothly scrolls so an element is visible |
| `use_api_to_fill(field_id, value)` | Fills a field via REST API (fast path) |

> Node.js analogy: This is like a `Page` object wrapper for Puppeteer — `page.click()`, `page.type()`, `page.screenshot()`.

---

### 📂 `tools/navigation.py` — Opening Pages

Two functions:

- **`run_step_navigate_to_sales_agent(agent)`** → Goes to the Sales Agent app for the specific application number
- **`run_step_navigate_to_documents(agent)`** → Goes to the Documents tab of the Sales Agent app

Both use `agent.page.goto(url)` (Playwright), then take screenshots.

---

### 📂 `tools/extraction.py` — Reading Applicant Data

**`run_step_extract_single_screen_data(agent)`**

**Strategy (tries in order):**
1. 🥇 **REST API first** → Calls `GET /api/applicant/{app_no}` — fast, structured JSON
2. 🥈 **VLM fallback** → Takes screenshot → sends to AI with a list of fields to extract
3. 🥉 **Mock data** → If VLM is disabled, uses hardcoded demo data

The extracted data (name, PAN, DOB, income, etc.) is saved to `agent._applicant_data`.

---

### 📂 `tools/verification.py` — Checking Documents With AI

**`run_step_verify_documents(agent)`**

Loops through document tabs (`PhotoIDProof`, `Others`, `NonMedicalDeclar`, etc.) and for each one:

1. Clicks the tab in the browser
2. Waits 4.5 seconds (PDF needs time to render)
3. Takes a screenshot
4. Sends screenshot + this prompt to the AI:

```
"What type of document is this?
Is it valid and does it match: Name: John Doe, PAN: ABCDE1234F?
Extract any ID numbers.
Give a confidence score (0.0 to 1.0)."
```

5. AI returns JSON like:
```json
{
  "doc_type": "PAN",
  "valid": true,
  "extracted_data": { "id_number": "ABCDE1234F" },
  "confidence": 0.95,
  "reasoning": "Clearly visible PAN card, number matches records"
}
```

6. Saves results: `pan_valid`, `aadhaar_valid`, etc.

---

### 📂 `tools/bank_statement.py` — Finding Minimum Balance

**`run_step_extract_min_balance(agent)`**

Same tab-clicking loop as verification, but this time asking the AI:

```
"Is this a bank statement?
What is the LOWEST value in the Balance column?"
```

It also **scrolls down** through the PDF to check multiple pages, keeping track of the lowest balance found anywhere in the document.

Result stored in: `agent._applicant_data["minimum_balance"]`

---

### 📂 `tools/checklist.py` — The Master Form Fill

**`run_step_final_checklist_update(agent)`**

This is the "write everything we've learned" step. It:

1. Navigates to the Underwriting App
2. Calls `fill_initial_case_details()` → fills Card 1 (app number, case type, gender)
3. Calls `update_checklist_with_verification_results()` → fills Card 2 (KYC — clicks YES/NO for each document)
4. Calls `fill_financial_sections()` → fills Card 3 (occupation, income, minimum balance)

All the actual clicking is done through `playwright_helper.py`'s `click_yn()`, `fill_text()`, and `select()` methods.

---

### 📂 `tools/submit.py` — Submitting the Form

**`run_step_submit(agent)`**

Calls `POST /api/submit` on the Underwriting App with:
```json
{
  "app_no": "OS121345678",
  "uw_decision": "Accept",
  "uw_remarks": "All checks passed — processed by automation agent",
  "performed_by": "AUTOMATION"
}
```

If the server says `422 Unprocessable` (some fields still empty), it calls `/api/submit/force` instead.

---

### 📂 `vlm_clients/` — AI Model Connectors

These are the **adapters** to different AI providers. They all implement the same interface defined in `base.py`.

Think of it like this in TypeScript:
```typescript
interface VLMClient {
  analyzeDocument(screenshot: Buffer, prompt: string): Promise<{ result, usage }>
  extractData(screenshot: Buffer, fields: string[]): Promise<{ data, usage }>
  analyzeAndAct(screenshot: Buffer, task: string, context: object): Promise<{ action, usage }>
}
```

All 4 clients (`openrouter`, `anthropic`, `openai`, `google`) implement these same methods, just calling different APIs.

**`base.py`** also defines:
- `VLMAction` — what action the AI wants to do (click, type, scroll)
- `VLMUsage` — how many tokens were used
- `SYSTEM_PROMPT` — instructions given to the AI at the start of every request
- Prompt templates for extraction and verification

---

## 🔄 How It All Connects (The Big Picture)

```
Dashboard (Streamlit)
    │
    │  calls
    ▼
run_automation_in_thread()   ← helpers.py
    │
    │  starts a background thread
    ▼
UnderwritingAgent.run()      ← agent.py
    │
    ├── Playwright browser opens
    │
    ├── Step 1: navigation.py  → goes to Sales Agent URL
    ├── Step 2: extraction.py  → reads applicant data (API or AI)
    ├── Step 3: navigation.py  → goes to Documents page
    ├── Step 4: verification.py → AI checks each document
    ├── Step 5: bank_statement.py → AI finds min balance
    ├── Step 6: checklist.py + fill.py → fills all form fields
    └── Step 7: submit.py → submits via REST API
    
    │ All steps communicate through:
    ▼
AutomationState (state)      ← helpers.py
    │
    │  Dashboard reads this state every few seconds
    ▼
Dashboard updates UI (progress, logs, screenshots, cost)
```

---

## 💡 Key Patterns to Understand

### Pattern 1: API First, VLM Fallback
The agent always tries the fast REST API path first. If it fails, it falls back to taking a screenshot and asking the AI. This is efficient and reduces AI costs.

### Pattern 2: Screenshot → AI → JSON Action
The core VLM loop:
1. Take screenshot
2. Send to AI with a structured prompt
3. AI returns JSON with answer
4. Agent uses the answer to do the next action

### Pattern 3: Thread Safety With `_lock`
Python has threading issues (like Node.js `race conditions`). Every time `AutomationState` writes data, it uses `with self._lock:` to prevent corruption. Node.js equivalent: using a `Mutex` or making operations atomic.

### Pattern 4: Graceful Errors
Every step has a `try/except` block. If a step fails, it logs the error and either raises (stops the agent) or defaults to a safe value (like marking all docs valid so the process can continue).

---

## 🏁 Summary — One-Liner Per File

| File | What It Does |
|---|---|
| `agent.py` | Orchestrates all steps, launches browser, runs in background thread |
| `helpers.py` | Shared state store + factory to create the right AI client |
| `playwright_helper.py` | All browser control: click, type, screenshot, scroll |
| `tools/navigation.py` | Opens specific URLs in the browser |
| `tools/extraction.py` | Reads applicant data (API or AI-from-screenshot) |
| `tools/verification.py` | AI verifies each uploaded document |
| `tools/bank_statement.py` | AI finds minimum balance in bank statements |
| `tools/checklist.py` | Coordinates the form-filling in the UW app |
| `tools/fill.py` | The actual fill functions for each section of the form |
| `tools/submit.py` | Submits the completed checklist via REST API |
| `vlm_clients/base.py` | AI client interface + prompt templates |
| `vlm_clients/openrouter_client.py` | OpenRouter API adapter |
| `vlm_clients/anthropic_client.py` | Claude API adapter |
| `vlm_clients/openai_client.py` | GPT-4o API adapter |
| `vlm_clients/google_client.py` | Gemini API adapter |
