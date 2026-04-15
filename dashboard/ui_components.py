def get_custom_css():
    return """<style>
  .main-header {
    background: linear-gradient(135deg, #1a237e, #283593);
    color: white;
    padding: 20px 24px;
    border-radius: 10px;
    margin-bottom: 20px;
  }
  .main-header h1 { margin: 0; font-size: 24px; }
  .main-header p { margin: 6px 0 0; opacity: 0.8; font-size: 14px; }

  .metric-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 14px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .metric-card .value { font-size: 28px; font-weight: bold; color: #1a237e; }
  .metric-card .label { font-size: 12px; color: #666; margin-top: 4px; }

  .log-container {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    height: 350px;
    overflow-y: auto;
    border: 1px solid #333;
  }
  .log-info { color: #9cdcfe; }
  .log-success { color: #4ec9b0; }
  .log-warning { color: #dcdcaa; }
  .log-error { color: #f44747; }
  .log-action { color: #b5cea8; }

  .step-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 13px;
  }
  .step-done { background: #e8f5e9; color: #2e7d32; }
  .step-active { background: #e3f2fd; color: #1565c0; animation: pulse 1.5s infinite; }
  .step-pending { background: #f5f5f5; color: #9e9e9e; }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
  }

  .app-frame {
    border: 2px solid #3f51b5;
    border-radius: 6px;
    overflow: hidden;
  }
  .app-frame-label {
    background: #3f51b5;
    color: white;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
  }

  .status-running { color: #1565c0; font-weight: bold; }
  .status-completed { color: #2e7d32; font-weight: bold; }
  .status-error { color: #c62828; font-weight: bold; }
  .status-idle { color: #666; }

  .live-log-container {
    background: #0d1117;
    color: #c9d1d9;
    padding: 10px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    height: 150px;
    overflow-y: auto;
    border: 1px solid #30363d;
    margin-top: 10px;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
  }
  .status-key {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 5px;
    font-size: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .status-key-label { font-weight: 600; color: #1a237e; }
  .status-key-value { color: #0d47a1; background: #e3f2fd; padding: 2px 8px; border-radius: 4px; font-weight: 700; }
</style>"""


def get_header_html():
    return """<div class="main-header">
  <h1>🤖 Insurance Underwriting Automation POC</h1>
  <p>AI-powered visual automation using computer-use / VLM models to automate the manual underwriting process</p>
</div>"""


def get_placeholder_cam_html():
    return """<div style="background:#f0f4ff;border:2px dashed #3f51b5;border-radius:8px;padding:60px;text-align:center;color:#3f51b5">
  <div style="font-size:48px">🎥</div>
  <div style="margin-top:12px;font-size:15px">Browser frames will stream here in real-time<br>while the automation is running</div>
</div>"""


def get_placeholder_screenshots_sales():
    return """<div style="background:#f0f4ff;border:2px dashed #3f51b5;border-radius:8px;padding:40px;text-align:center;color:#3f51b5">
  <div style="font-size:40px">📋</div>
  <div style="margin-top:8px;font-size:14px">Sales Agent App<br>Screenshot will appear here</div>
</div>"""


def get_placeholder_screenshots_uw():
    return """<div style="background:#f0fff4;border:2px dashed #43a047;border-radius:8px;padding:40px;text-align:center;color:#43a047">
  <div style="font-size:40px">✅</div>
  <div style="margin-top:8px;font-size:14px">Underwriting Checklist<br>Screenshot will appear here</div>
</div>"""


def get_architecture_diagram():
    return """```
┌─────────────────────────────────────────────────────────────────┐
│                   INSURANCE UW AUTOMATION POC                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────────────────┐    │
│  │  Sales Agent App  │      │  Underwriting Checklist App  │    │
│  │   (Port 5001)     │      │        (Port 5002)            │    │
│  │                  │      │                              │    │
│  │ • Case Queue     │      │ • Card 1: Case Details       │    │
│  │ • Personal Info  │      │ • Card 2: KYC Checks         │    │
│  │ • Doc Viewer     │      │   - PAN Validation           │    │
│  │   - PAN Card     │      │   - Aadhaar Validation       │    │
│  │   - Bank Stmt    │      │   - Address Proof            │    │
│  │   - Photo Validation     │   - Bank Validation          │    │
│  └────────┬─────────┘      │ • Card 3: Financial           │    │
│           │                │   - Occupation               │    │
│           │                │   - Income Check             │    │
│           │                │   - Education                │    │
│           │                │   - Nominee                  │    │
│           │                └──────────────┬───────────────┘    │
│           │                               │                     │
│  ┌────────▼───────────────────────────────▼───────────────┐    │
│  │              INTELLIGENCE LAYER (Python)                │    │
│  │                                                         │    │
│  │  UnderwritingAgent                                      │    │
│  │  ├── Playwright Browser Control                        │    │
│  │  │   └── Takes screenshots at each step               │    │
│  │  │                                                      │    │
│  │  └── VLM Client (pluggable)                            │    │
│  │      ├── OpenRouter → Qwen2.5-VL ◄── DEFAULT          │    │
│  │      ├── Anthropic  → Claude 3.5 Sonnet               │    │
│  │      ├── OpenAI     → GPT-4o                           │    │
│  │      └── Google     → Gemini 1.5 Pro                   │    │
│  │                                                         │    │
│  │  Computer Use Loop:                                     │    │
│  │  screenshot → VLM analysis → action → verify → next    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐    │
│  │         STREAMLIT DASHBOARD (Port 8501)                 │    │
│  │                                                         │    │
│  │  • Model selection & API key configuration              │    │
│  │  • Start / Stop / Reset controls                        │    │
│  │  • Live progress tracking                               │    │
│  │  • Screenshot viewer                                    │    │
│  │  • Action log                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```"""


def get_architecture_desc():
    return """#### 🔄 Computer Use Loop

```
1. Navigate to Sales Agent App
   ↓
2. Screenshot → VLM → Extract Data
   (name, PAN, Aadhaar, bank, etc.)
   ↓
3. Navigate to Underwriting App
   ↓
4. For each section:
   ├── Take screenshot
   ├── VLM analyzes: "What to do next?"
   ├── VLM returns: {
   │     "action": "click",
   │     "x": 245,
   │     "y": 612,
   │     "element": "Yes btn for PAN copy",
   │     "reasoning": "PAN doc is uploaded"
   │   }
   ├── Playwright executes action
   └── Verify → next step
   ↓
5. Checklist Complete
```

#### 🤖 Supported Models

| Provider | Model | Notes |
|----------|-------|-------|
| OpenRouter | Qwen2.5-VL-72B | ⭐ Default |
| OpenRouter | Qwen2-VL-72B | Good |
| OpenRouter | Qwen2-VL-7B | Fast |
| Anthropic | Claude 3.5 Sonnet | Premium |
| OpenAI | GPT-4o | Premium |
| Google | Gemini 1.5 Pro | Good |

#### 📦 Tech Stack
- **Flask** - Web apps
- **Playwright** - Browser control
- **Pillow** - Image processing
- **httpx** - API calls
- **Streamlit** - Dashboard"""
