"""
Streamlit Orchestration Dashboard for the Insurance Underwriting POC.
"""

import sys
import os
import time
import base64
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from config import (
    VLM_MODELS,
    SALES_AGENT_URL,
    UNDERWRITING_URL,
    DEFAULT_OPENROUTER_KEY,
    DEFAULT_OPENAI_KEY,
    APPLICANT_DATA,
)

from crud import (
    get_state,
    start_automation,
    stop_automation,
    reset_automation,
    fetch_checklist_status,
)
from service import render_log, calculate_step_visual, construct_actions_dataframe
from ui_components import (
    get_custom_css,
    get_header_html,
    get_placeholder_cam_html,
    get_placeholder_screenshots_sales,
    get_placeholder_screenshots_uw,
    get_architecture_diagram,
    get_architecture_desc,
)
from constants import STEPS, DUMMY_LOG

st.set_page_config(
    page_title="Underwriting Automation POC",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

if "automation_state" not in st.session_state:
    st.session_state.automation_state = None
if "automation_thread" not in st.session_state:
    st.session_state.automation_thread = None
if "last_log_count" not in st.session_state:
    st.session_state.last_log_count = 0
if "cached_form_data" not in st.session_state:
    st.session_state.cached_form_data = None
if "extracted_doc_data" not in st.session_state:
    st.session_state.extracted_doc_data = None
if "extracted_doc_image" not in st.session_state:
    st.session_state.extracted_doc_image = None
if "extracted_doc_pages" not in st.session_state:
    st.session_state.extracted_doc_pages = []  # list of image bytes, one per page
if "validation_report" not in st.session_state:
    st.session_state.validation_report = None
if "rules_report" not in st.session_state:
    st.session_state.rules_report = None

st.markdown(get_header_html(), unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    st.markdown("**VLM Model**")
    selected_model_name = st.selectbox(
        "Select Model", options=list(VLM_MODELS.keys()), index=0
    )
    model_config = VLM_MODELS[selected_model_name]

    st.markdown(f"Provider: `{model_config['provider']}`")
    st.markdown(f"Model ID: `{model_config['model_id']}`")
    st.divider()

    st.markdown("**API Keys**")
    provider = model_config["provider"]
    if provider == "openrouter":
        api_key = st.text_input(
            "OpenRouter API Key", value=DEFAULT_OPENROUTER_KEY, type="password"
        )
    elif provider == "openai":
        api_key = st.text_input("OpenAI API Key", value=DEFAULT_OPENAI_KEY, type="password")
    elif provider == "google":
        api_key = st.text_input("Google AI API Key", type="password")
    else:
        api_key = st.text_input("API Key", type="password")
    st.divider()

    st.markdown("**Azure Document Intelligence**")
    from config import AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY, AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID
    azure_endpoint = st.text_input("Azure Endpoint", value=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT)
    azure_key = st.text_input("Azure Key", value=AZURE_DOCUMENT_INTELLIGENCE_KEY, type="password")
    azure_model_id = st.text_input("Model ID", value=AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID, help="Leave as 'prebuilt-document' or enter your custom model ID.")
    st.divider()

    st.markdown("**Automation Settings**")
    use_visual_mode = st.toggle("🤖 VLM Visual Mode", value=True)
    step_delay = st.slider(
        "Step Delay (seconds)", min_value=0.5, max_value=5.0, value=1.5, step=0.5
    )
    app_no = st.text_input("Application Number", value="OS121345678")
    st.divider()

    headed_mode = False
    record_video = False


    st.markdown("**🔗 Application Links**")
    st.markdown(f"[📋 Sales Agent App]({SALES_AGENT_URL}) (port 5001)")
    st.markdown(f"[✅ Underwriting App]({UNDERWRITING_URL}) (port 5002)")
    st.divider()
    st.markdown("**📄 Document Extraction**")
    uploaded_file = st.file_uploader(
        "Upload Insurance Document",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Supports images (PNG/JPG) and multi-page PDF documents.",
    )
    if st.button("🔍 Extract Fields", use_container_width=True):
        if not uploaded_file:
            st.warning("⚠️ Please upload a document first.")
        elif not azure_endpoint or not azure_key:
            st.warning("⚠️ Please enter Azure Document Intelligence Endpoint and Key above.")
        else:
            with st.spinner("Extracting data via Azure Document Intelligence…"):
                try:
                    from intelligence.tools.extraction import extract_document_fields
                    
                    total_pages_hint = [1]
                    progress_bar = st.empty()

                    def _on_progress(current: int, total: int):
                        total_pages_hint[0] = total
                        progress_bar.progress((current - 1) / total, text=f"Processing page {current} of {total}…")

                    merged_data, page_images, avg_confidence, total_input, total_output, model_id = extract_document_fields(
                        file_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                        azure_endpoint=azure_endpoint,
                        azure_key=azure_key,
                        azure_model_id=azure_model_id,
                        progress_callback=_on_progress,
                    )
                    progress_bar.progress(1.0, text="Done!")

                    from crud import get_state as _gs
                    current_state = _gs()
                    current_state.update_usage(total_input, total_output, model_id)
                    current_state.image_confidence = avg_confidence
                    current_state.doc_confidences["Uploaded Document"] = avg_confidence

                    from intelligence.tools.validation_agent import validate_fields
                    from intelligence.tools.business_rules_agent import check_business_rules

                    val_report = validate_fields(merged_data)
                    rules_report = check_business_rules(merged_data, parsed_values=val_report.get("_parsed"))

                    st.session_state.validation_report = val_report
                    st.session_state.rules_report = rules_report
                    st.session_state.extracted_doc_data = merged_data
                    st.session_state.extracted_doc_pages = page_images
                    st.session_state.extracted_doc_image = page_images[0]

                    n = total_pages_hint[0]
                    label = f"{n}-page PDF" if uploaded_file.name.lower().endswith(".pdf") else "document"
                    st.success(f"Extraction complete ({label})! Check the '📄 Extraction Review' tab.")
                except Exception as e:
                    st.error(f"Extraction failed: {str(e)}")
state = get_state()

col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

with col_s1:
    if state.running:
        st.markdown(
            "**Status:** <span class='status-running'>🔄 Running</span>",
            unsafe_allow_html=True,
        )
    elif state.completed:
        st.markdown(
            "**Status:** <span class='status-completed'>✅ Completed</span>",
            unsafe_allow_html=True,
        )
    elif state.error:
        st.markdown(
            "**Status:** <span class='status-error'>❌ Error</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "**Status:** <span class='status-idle'>⏸ Idle</span>",
            unsafe_allow_html=True,
        )

with col_s2:
    st.markdown(f"**Progress:** {state.progress * 100:.0f}%")

with col_s3:
    st.markdown(f"**Actions:** {len(state.actions_taken)}")

with col_s4:
    st.markdown(f"**Screenshots:** {len(state.screenshots)}")

with col_s5:
    if state.start_time and state.end_time:
        elapsed = (state.end_time - state.start_time).total_seconds()
        st.markdown(f"**Time:** {elapsed:.1f}s")
    elif state.start_time:
        from datetime import datetime

        elapsed = (datetime.now() - state.start_time).total_seconds()
        st.markdown(f"**Time:** {elapsed:.1f}s")
    else:
        st.markdown("**Time:** -")

st.progress(state.progress)

# NEW: Token Usage & Cost & Confidence Metrics
u_col1, u_col2, u_col3, u_col4, u_col5 = st.columns(5)
with u_col1:
    st.markdown(f"<div class='metric-box'><b>Input Tokens:</b> {state.input_tokens:,}</div>", unsafe_allow_html=True)
with u_col2:
    st.markdown(f"<div class='metric-box'><b>Output Tokens:</b> {state.output_tokens:,}</div>", unsafe_allow_html=True)
with u_col3:
    st.markdown(f"<div class='metric-box'><b>Total Tokens:</b> {state.input_tokens + state.output_tokens:,}</div>", unsafe_allow_html=True)
with u_col4:
    st.markdown(f"<div class='metric-box'><b>Est. Cost:</b> <span style='color:#2e7d32;font-weight:bold'>${state.total_cost:.4f}</span></div>", unsafe_allow_html=True)

conf = state.image_confidence * 100
conf_color = "#2e7d32" if conf >= 80 else "#f9a825" if conf >= 50 else "#c62828"
handoff_note = " (Handoff!)" if conf < 50 and state.completed else ""

with u_col5:
    st.markdown(f"<div class='metric-box' title='Overall Average'><b>Overall Confidence:</b> <span style='color:{conf_color};font-weight:bold'>{conf:.1f}%{handoff_note}</span></div>", unsafe_allow_html=True)

if state.doc_confidences:
    st.markdown("<div style='margin-top: 10px;'><b>📄 Document Confidence Breakdown:</b></div>", unsafe_allow_html=True)
    doc_cols = st.columns(len(state.doc_confidences))
    for idx, (doc_name, d_conf) in enumerate(state.doc_confidences.items()):
        val = d_conf * 100
        d_color = "#2e7d32" if val >= 80 else "#f9a825" if val >= 50 else "#c62828"
        with doc_cols[idx]:
            st.markdown(f"<div class='doc-conf-box'><b>{doc_name}</b><br><span style='color:{d_color};font-weight:bold;font-size:16px;'>{val:.0f}%</span></div>", unsafe_allow_html=True)

st.markdown("""
<style>
.metric-box {
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    text-align: center;
    font-size: 14px;
}
.doc-conf-box {
    background-color: #ffffff;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
    text-align: center;
    font-size: 12px;
    margin-top: 5px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([2, 2, 2, 4])

with col_btn1:
    start_disabled = state.running or not api_key
    if st.button(
        "▶ Start Automation",
        type="primary",
        disabled=start_disabled,
        use_container_width=True,
    ):
        st.session_state.cached_form_data = None
        with st.spinner("Starting automation agent..."):
            start_automation(
                SALES_AGENT_URL,
                UNDERWRITING_URL,
                model_config,
                api_key,
                use_visual_mode,
                step_delay,
                app_no,
                headed=headed_mode,
                record_video=record_video,
            )
        st.rerun()

with col_btn2:
    if st.button("⏹ Stop", disabled=not state.running, use_container_width=True):
        stop_automation()
        st.rerun()

with col_btn3:
    if st.button("🔄 Reset", disabled=state.running, use_container_width=True):
        reset_automation(UNDERWRITING_URL)
        st.rerun()

with col_btn4:
    pass # Status now handled below in the Live Log section

st.markdown("---")

# NEW: Live Execution Monitor
if state.running or state.completed or state.log_entries:
    st.markdown("#### ⚡ Live Execution Monitor")
    
    # Status Key Row
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown(f'''<div class="status-key">
            <span class="status-key-label">🗺️ Current Step:</span>
            <span class="status-key-value">{state.current_step if state.running else ("Complete" if state.completed else "Idle")}</span>
        </div>''', unsafe_allow_html=True)
    with s_col2:
        st.markdown(f'''<div class="status-key">
            <span class="status-key-label">📍 Active Section:</span>
            <span class="status-key-value">{state.current_section if state.running else ("N/A")}</span>
        </div>''', unsafe_allow_html=True)

    # Line-by-line Action Log
    if state.log_entries:
        log_html = render_log(state.log_entries[-15:]) # Last 15 entries for "line by line" feel
        st.markdown(f'<div class="live-log-container">{log_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("Waiting for automation log...")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📊 Dashboard",
        "🎥 Live View",
        "📸 Screenshots",
        "📋 Action Log",
        "📁 Architecture",
        "📄 Extraction Review",
    ]
)

with tab1:
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown("#### 🔄 Automation Steps")
        for i, (step_id, step_name) in enumerate(STEPS):
            visual = calculate_step_visual(state.progress, i, state.running)
            st.markdown(
                f'<div style="background:{visual["color"]};color:{visual["text_color"]};padding:5px 10px;border-radius:5px;margin-bottom:3px;font-size:13px">'
                f"{visual['icon']} {step_name}"
                f"</div>",
                unsafe_allow_html=True,
            )
    with col_right:
        cs = fetch_checklist_status(UNDERWRITING_URL)
        if cs:
            st.markdown("#### 📝 Submitted Underwriter Form Data")
            
            if state.running or state.completed:
                # Prevent overwriting cache with a freshly spawned blank checklist after submission
                is_fresh = not cs.get("cards", {}).get("card1", {}).get("fields", {}).get("case_type")
                if not is_fresh or st.session_state.cached_form_data is None:
                    st.session_state.cached_form_data = cs
                
            data_to_display = st.session_state.cached_form_data if st.session_state.cached_form_data else cs
            
            markdown_table = "| Field | Value |\n|-------|-------|\n"
            
            if "card1" in data_to_display["cards"]:
                for k, v in data_to_display["cards"]["card1"].get("fields", {}).items():
                    val = v if v not in [None, ""] else "-"
                    markdown_table += f"| **{k.replace('_', ' ').title()}** | {val} |\n"
            
            for card_key in ["card2", "card3"]:
                if card_key in data_to_display["cards"]:
                    for sec_key, sec in data_to_display["cards"][card_key].get("sections", {}).items():
                        if "fields" in sec:
                            for k, v in sec["fields"].items():
                                val = v if v not in [None, ""] else "-"
                                if isinstance(val, bool):
                                    val = "Yes" if val else "No"
                                markdown_table += f"| **{k.replace('_', ' ').title()}** | `{val}` |\n"
                                
            st.markdown(markdown_table)
        else:
            st.info("Checklist app not yet started. Form data will appear here once available.")

with tab2:
    st.markdown("#### 🎥 Live Browser View")
    if state.running:
        st.caption(
            "The image below auto-refreshes every 2 seconds while automation is running."
        )
    elif state.video_path:
        st.success(f"✅ Session recording saved: `{state.video_path}`")
        try:
            with open(state.video_path, "rb") as vf:
                video_bytes = vf.read()
            st.video(video_bytes, format="video/webm")
            st.download_button(
                "⬇️ Download Recording (.webm)",
                data=video_bytes,
                file_name="uw_automation_session.webm",
                mime="video/webm",
            )
        except Exception as ve:
            st.warning(f"Could not load video file: {ve}")
    elif state.completed and not state.video_path:
        st.info(
            "No video recorded for this session. Enable **Record Session Video** in the sidebar before starting."
        )
    else:
        st.info("Live view will appear here once automation starts.")

    if state.latest_screenshot_b64:
        img_bytes = base64.b64decode(state.latest_screenshot_b64)
        st.image(img_bytes, caption="Latest browser frame", use_container_width=True)
    elif not (state.video_path or state.completed):
        st.markdown(get_placeholder_cam_html(), unsafe_allow_html=True)

with tab3:
    st.markdown("#### 📸 Automation Screenshots")
    st.caption(
        "Screenshots captured during automation showing the agent's view at each step"
    )

    if state.screenshots:
        screenshots = state.screenshots
        for i in range(0, len(screenshots), 2):
            col_a, col_b = st.columns(2)
            for j, col in enumerate([col_a, col_b]):
                idx = i + j
                if idx < len(screenshots):
                    label, b64_data = screenshots[idx]
                    with col:
                        st.markdown(f"**{label}**")
                        st.image(
                            base64.b64decode(b64_data),
                            use_container_width=True,
                            caption=f"Step {idx + 1}: {label}",
                        )
    else:
        st.info("Screenshots will appear here as the automation runs.")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(get_placeholder_screenshots_sales(), unsafe_allow_html=True)
        with col_b:
            st.markdown(get_placeholder_screenshots_uw(), unsafe_allow_html=True)

with tab4:
    st.markdown("#### 📋 Automation Action Log")
    if state.log_entries:
        st.markdown(
            f'<div class="log-container">{render_log(state.log_entries)}</div>',
            unsafe_allow_html=True,
        )
        if state.actions_taken:
            st.markdown("#### 🎯 Actions Taken Summary")
            st.dataframe(
                construct_actions_dataframe(state.actions_taken),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Action log will appear here once automation starts.")
        st.code(DUMMY_LOG, language="text")

with tab5:
    st.markdown("#### 🏗️ System Architecture")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(get_architecture_diagram())
    with col_b:
        st.markdown(get_architecture_desc())

with tab6:
    st.markdown("#### 📄 Extracted Document Review")
    if st.session_state.extracted_doc_data and st.session_state.extracted_doc_pages:
        pages = st.session_state.extracted_doc_pages
        rev_col1, rev_col2 = st.columns([1, 1])
        with rev_col1:
            st.markdown(f"**Uploaded Document** ({len(pages)} page{'s' if len(pages) > 1 else ''})")
            if len(pages) == 1:
                st.image(pages[0], use_container_width=True)
            else:
                # Show a page selector for multi-page PDFs
                page_num = st.number_input(
                    "Page", min_value=1, max_value=len(pages), value=1, step=1,
                    key="doc_review_page"
                )
                st.image(pages[page_num - 1], caption=f"Page {page_num} of {len(pages)}", use_container_width=True)
        with rev_col2:
            st.markdown("**1. Extracted Data (merged across all pages)**")
            with st.expander("View Raw JSON", expanded=False):
                st.json(st.session_state.extracted_doc_data)

            if st.session_state.validation_report:
                vr = st.session_state.validation_report
                st.markdown(f"**2. Field Validation** (Pass: {vr['summary']['pass']} | Fail: {vr['summary']['fail']} | Warn: {vr['summary']['warn']})")
                
                html_val = "<table style='width: 100%; border-collapse: collapse; font-size: 13px;'><tr><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Check</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Value</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Status</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Message</th></tr>"
                for c in vr["checks"]:
                    color = "green" if c["status"] == "pass" else ("orange" if c["status"] == "warn" else "red")
                    icon = "✅" if c["status"] == "pass" else ("⚠️" if c["status"] == "warn" else "❌")
                    html_val += f"<tr><td style='border-bottom: 1px solid #eee; padding: 4px;'>{c['check']}</td><td style='border-bottom: 1px solid #eee; padding: 4px;'>{c['value']}</td><td style='border-bottom: 1px solid #eee; padding: 4px; color:{color}'><b>{icon} {c['status'].upper()}</b></td><td style='border-bottom: 1px solid #eee; padding: 4px;'>{c['message']}</td></tr>"
                html_val += "</table><br/>"
                st.markdown(html_val, unsafe_allow_html=True)

            if st.session_state.rules_report:
                rr = st.session_state.rules_report
                st.markdown(f"**3. Business Rules** (Pass: {rr['summary']['pass']} | Error: {rr['summary']['error']} | Warn: {rr['summary']['warn']})")
                
                html_rules = "<table style='width: 100%; border-collapse: collapse; font-size: 13px;'><tr><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Rule</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Status</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Message</th><th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Code</th></tr>"
                for r in rr["rules"]:
                    color = "green" if r["status"] == "pass" else ("orange" if r["status"] == "warn" else "red")
                    icon = "✅" if r["status"] == "pass" else ("⚠️" if r["status"] == "warn" else "❌")
                    code_html = f"<code>{r['code']}</code>" if r['code'] else ""
                    html_rules += f"<tr><td style='border-bottom: 1px solid #eee; padding: 4px;'>{r['rule']}</td><td style='border-bottom: 1px solid #eee; padding: 4px; color:{color}'><b>{icon} {r['status'].upper()}</b></td><td style='border-bottom: 1px solid #eee; padding: 4px;'>{r['message']}</td><td style='border-bottom: 1px solid #eee; padding: 4px;'>{code_html}</td></tr>"
                html_rules += "</table>"
                st.markdown(html_rules, unsafe_allow_html=True)
    else:
        st.info("Upload and extract a document from the sidebar to review it here.")

if state.running:
    time.sleep(2)
    st.rerun()
elif (
    state.running is False and state.start_time and not state.completed and state.error
):
    pass
