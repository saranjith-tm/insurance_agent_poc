"""
Streamlit Orchestration Dashboard - Home / Agent Configuration
"""

import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
from config import (
    VLM_MODELS,
    SALES_AGENT_URL,
    UNDERWRITING_URL,
    DEFAULT_OPENROUTER_KEY,
    DEFAULT_OPENAI_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID,
)
from ui_components import get_custom_css, get_header_html

st.set_page_config(
    page_title="Underwriting Automation POC",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

# ── shared session state ──────────────────────────────────────────────────────
from crud import init_session_config
init_session_config()

# ── header ────────────────────────────────────────────────────────────────────
st.markdown(get_header_html(), unsafe_allow_html=True)

st.markdown("## ⚙️ Agent Configuration")
st.markdown(
    "Configure all agent settings here. These are shared across the **Document Extraction** "
    "and **Underwriter Automation** pages."
)
st.divider()


# ── VLM Model ─────────────────────────────────────────────────────────────────
st.markdown("### 🤖 VLM Model")
selected_model_name = st.selectbox(
    "Select Model",
    options=list(VLM_MODELS.keys()),
    index=list(VLM_MODELS.keys()).index(st.session_state.cfg_model_name),
    key="_sel_model",
)
st.session_state.cfg_model_name = selected_model_name
model_config = VLM_MODELS[selected_model_name]

st.divider()

# ── API Keys ──────────────────────────────────────────────────────────────────
st.markdown("### 🔑 API Keys")
provider = model_config["provider"]
if provider == "openrouter":
    api_key = st.text_input(
        "OpenRouter API Key",
        value=st.session_state.cfg_api_key,
        type="password",
        key="_ak_openrouter",
    )
elif provider == "openai":
    api_key = st.text_input(
        "OpenAI API Key",
        value=st.session_state.cfg_api_key,
        type="password",
        key="_ak_openai",
    )
elif provider == "google":
    api_key = st.text_input(
        "Google AI API Key",
        value=st.session_state.cfg_api_key,
        type="password",
        key="_ak_google",
    )
else:
    api_key = st.text_input(
        "API Key",
        value=st.session_state.cfg_api_key,
        type="password",
        key="_ak_other",
    )
st.session_state.cfg_api_key = api_key

st.divider()

# ── Azure Document Intelligence ───────────────────────────────────────────────
st.markdown("### 📑 Azure Document Intelligence")
az1, az2, az3 = st.columns(3)
with az1:
    azure_endpoint = st.text_input(
        "Azure Endpoint",
        value=st.session_state.cfg_azure_endpoint,
        key="_az_ep",
    )
    st.session_state.cfg_azure_endpoint = azure_endpoint
with az2:
    azure_key = st.text_input(
        "Azure Key",
        value=st.session_state.cfg_azure_key,
        type="password",
        key="_az_key",
    )
    st.session_state.cfg_azure_key = azure_key
with az3:
    azure_model_id = st.text_input(
        "Model ID",
        value=st.session_state.cfg_azure_model_id,
        help="Leave as 'prebuilt-document' or enter your custom model ID.",
        key="_az_mid",
    )
    st.session_state.cfg_azure_model_id = azure_model_id

st.divider()

# ── Automation Settings ───────────────────────────────────────────────────────
st.markdown("### 🛠️ Automation Settings")
as1, as2 = st.columns(2)
with as1:
    use_visual_mode = st.toggle(
        "🤖 VLM Visual Mode",
        value=st.session_state.cfg_use_visual_mode,
        key="_vis_mode",
    )
    st.session_state.cfg_use_visual_mode = use_visual_mode
with as2:
    step_delay = st.slider(
        "Step Delay (seconds)",
        min_value=0.5,
        max_value=5.0,
        value=st.session_state.cfg_step_delay,
        step=0.5,
        key="_step_delay",
    )
    st.session_state.cfg_step_delay = step_delay

st.divider()

# ── Application Links ─────────────────────────────────────────────────────────
st.markdown("### 🔗 Application Links")
lc1, lc2 = st.columns(2)
with lc1:
    st.markdown(
        f"""<div style="background:#e3f2fd;border-radius:8px;padding:16px;">
            <b>📋 Sales Agent App</b><br>
            <a href="{SALES_AGENT_URL}" target="_blank">{SALES_AGENT_URL}</a>
            <br><span style="font-size:12px;color:#555;">Port 5001</span>
        </div>""",
        unsafe_allow_html=True,
    )
with lc2:
    st.markdown(
        f"""<div style="background:#e8f5e9;border-radius:8px;padding:16px;">
            <b>✅ Underwriting App</b><br>
            <a href="{UNDERWRITING_URL}" target="_blank">{UNDERWRITING_URL}</a>
            <br><span style="font-size:12px;color:#555;">Port 5002</span>
        </div>""",
        unsafe_allow_html=True,
    )

st.info("👈 Use the **sidebar** to navigate to Document Extraction or Underwriter Automation.")
