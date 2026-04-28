import os
import sys
import httpx
import streamlit as st


def get_state():
    if st.session_state.automation_state is None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from intelligence.agent import AutomationState

        st.session_state.automation_state = AutomationState()
    return st.session_state.automation_state


def start_automation(
    SALES_AGENT_URL,
    UNDERWRITING_URL,
    model_config: dict,
    api_key: str,
    use_visual_mode: bool,
    step_delay: float,
    app_no: str,
    headed: bool = False,
    record_video: bool = False,
):
    import os
    from intelligence.agent import run_automation_in_thread, AutomationState

    state = AutomationState()
    st.session_state.automation_state = state
    st.session_state.last_log_count = 0

    video_dir = os.path.join(os.path.dirname(__file__), "..", "recordings")

    thread = run_automation_in_thread(
        model_config=model_config,
        api_key=api_key,
        sales_agent_url=SALES_AGENT_URL,
        underwriting_url=UNDERWRITING_URL,
        application_no=app_no,
        state=state,
        use_visual_mode=use_visual_mode,
        step_delay=step_delay,
        headed=headed,
        record_video=record_video,
        video_dir=video_dir,
    )
    st.session_state.automation_thread = thread
    return state


def stop_automation():
    state = st.session_state.automation_state
    if state:
        state.running = False
        state.log("⛔ Automation stopped by user", "warning")


def reset_automation(UNDERWRITING_URL):
    try:
        httpx.post(f"{UNDERWRITING_URL}/api/reset", timeout=5)
    except Exception:
        pass
    from intelligence.agent import AutomationState

    st.session_state.automation_state = AutomationState()
    st.session_state.last_log_count = 0


def fetch_checklist_status(UNDERWRITING_URL):
    try:
        resp = httpx.get(f"{UNDERWRITING_URL}/api/state", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None


def init_session_config():
    """Initialize shared session state with defaults if not already present."""
    from config import (
        VLM_MODELS,
        DEFAULT_OPENROUTER_KEY,
        DEFAULT_OPENAI_KEY,
        AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        AZURE_DOCUMENT_INTELLIGENCE_KEY,
        AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID,
    )

    defaults = {
        "automation_state": None,
        "automation_thread": None,
        "last_log_count": 0,
        "cached_form_data": None,
        "extracted_doc_data": None,
        "extracted_doc_image": None,
        "extracted_doc_pages": [],
        "validation_report": None,
        "rules_report": None,
        # configuration (persisted across pages via session state)
        "cfg_model_name": list(VLM_MODELS.keys())[0],
        "cfg_api_key": DEFAULT_OPENROUTER_KEY,
        "cfg_azure_endpoint": AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        "cfg_azure_key": AZURE_DOCUMENT_INTELLIGENCE_KEY,
        "cfg_azure_model_id": AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID,
        "cfg_use_visual_mode": True,
        "cfg_step_delay": 1.5,
        "cfg_app_no": "OS121345678",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
