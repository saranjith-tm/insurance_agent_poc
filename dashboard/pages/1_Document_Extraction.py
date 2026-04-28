"""
Document Extraction Page
Upload insurance documents, extract fields via Azure Document Intelligence,
and review validation + business rules results.
"""

import sys
import os

# Ensure project root is on path so both `dashboard.*` and top-level modules resolve
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
from ui_components import get_custom_css, get_header_html

st.set_page_config(
    page_title="Document Extraction | Underwriting POC",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

from dashboard.crud import init_session_config
init_session_config()

# ── header ────────────────────────────────────────────────────────────────────
st.markdown(get_header_html(), unsafe_allow_html=True)
st.markdown("## 📄 Document Extraction")
st.markdown(
    "Upload an insurance document (image or PDF). The Azure Document Intelligence service "
    "will extract all fields, which are then validated against field-level rules and business rules."
)
st.divider()



# ── upload + extract ──────────────────────────────────────────────────────────
st.markdown("### 📤 Upload Document")
uploaded_file = st.file_uploader(
    "Choose an insurance document",
    type=["png", "jpg", "jpeg", "pdf"],
    help="Supports images (PNG/JPG) and multi-page PDF documents.",
)

if uploaded_file:
    st.success(f"✅ File ready: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

col_btn, col_status = st.columns([1, 3])
with col_btn:
    extract_clicked = st.button(
        "🔍 Extract Fields",
        use_container_width=True,
        type="primary",
        disabled=not uploaded_file,
    )

if extract_clicked:
    azure_endpoint = st.session_state.cfg_azure_endpoint
    azure_key = st.session_state.cfg_azure_key
    azure_model_id = st.session_state.cfg_azure_model_id

    if not azure_endpoint or not azure_key:
        st.error("❌ Azure Endpoint and Key are required. Configure them on the **Home** page.")
    else:
        with st.spinner("Extracting data via Azure Document Intelligence…"):
            try:
                from intelligence.tools.extraction import extract_document_fields
                from dashboard.crud import get_state

                total_pages_hint = [1]
                progress_bar = st.empty()

                def _on_progress(current: int, total: int):
                    total_pages_hint[0] = total
                    progress_bar.progress(
                        (current - 1) / total,
                        text=f"Processing page {current} of {total}…",
                    )

                (
                    merged_data,
                    page_images,
                    avg_confidence,
                    total_input,
                    total_output,
                    model_id,
                ) = extract_document_fields(
                    file_bytes=uploaded_file.getvalue(),
                    filename=uploaded_file.name,
                    azure_endpoint=azure_endpoint,
                    azure_key=azure_key,
                    azure_model_id=azure_model_id,
                    progress_callback=_on_progress,
                )
                progress_bar.progress(1.0, text="Done!")

                current_state = get_state()
                current_state.update_usage(total_input, total_output, model_id)
                current_state.image_confidence = avg_confidence
                current_state.doc_confidences["Uploaded Document"] = avg_confidence

                from intelligence.tools.validation_agent import validate_fields
                from intelligence.tools.business_rules_agent import check_business_rules

                val_report = validate_fields(merged_data)
                rules_report = check_business_rules(
                    merged_data, parsed_values=val_report.get("_parsed")
                )

                st.session_state.validation_report = val_report
                st.session_state.rules_report = rules_report
                st.session_state.extracted_doc_data = merged_data
                st.session_state.extracted_doc_pages = page_images
                st.session_state.extracted_doc_image = page_images[0]

                n = total_pages_hint[0]
                label = (
                    f"{n}-page PDF"
                    if uploaded_file.name.lower().endswith(".pdf")
                    else "document"
                )
                st.success(f"✅ Extraction complete ({label})! Review results below.")
            except Exception as e:
                st.error(f"Extraction failed: {str(e)}")

st.divider()

# ── extraction review ─────────────────────────────────────────────────────────
st.markdown("### 🔬 Extraction Review")

if st.session_state.get("extracted_doc_data") and st.session_state.get("extracted_doc_pages"):
    pages = st.session_state.extracted_doc_pages
    data = st.session_state.extracted_doc_data
    field_confidences = data.get("_field_confidences", {})
    low_conf_fields = {k: v for k, v in field_confidences.items() if v < 0.75}

    if len(low_conf_fields) >= 3:
        st.warning(f"⚠️ {len(low_conf_fields)} fields have extraction confidence below 75%. Human review is recommended.")
        if st.button("👁️ Human Review"):
            st.session_state.show_human_review = not st.session_state.get("show_human_review", False)
            
        if st.session_state.get("show_human_review", False):
            st.markdown("#### 🔍 Low Confidence Fields (Requires Human Review)")
            html_low = (
                "<table style='width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 15px;'>"
                "<tr>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Field</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Extracted Value</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Confidence</th>"
                "</tr>"
            )
            for k, v in low_conf_fields.items():
                val = data.get(k, "")
                html_low += (
                    f"<tr>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{k}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{val}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px;color:red'>{(v*100):.1f}%</td>"
                    f"</tr>"
                )
            html_low += "</table>"
            st.markdown(html_low, unsafe_allow_html=True)
            st.divider()

    rev_col1, rev_col2 = st.columns([1, 1])

    with rev_col1:
        st.markdown(f"**Uploaded Document** ({len(pages)} page{'s' if len(pages) > 1 else ''})")
        if len(pages) == 1:
            st.image(pages[0], use_container_width=True)
        else:
            page_num = st.number_input(
                "Page",
                min_value=1,
                max_value=len(pages),
                value=1,
                step=1,
                key="doc_review_page",
            )
            st.image(
                pages[page_num - 1],
                caption=f"Page {page_num} of {len(pages)}",
                use_container_width=True,
            )

    with rev_col2:
        # ── Extracted JSON ────────────────────────────────────────────────────
        st.markdown("**1. Extracted Data (merged across all pages)**")
        with st.expander("View Raw JSON", expanded=False):
            st.json(st.session_state.extracted_doc_data)

        # ── Field Validation ──────────────────────────────────────────────────
        if st.session_state.validation_report:
            vr = st.session_state.validation_report
            st.markdown(
                f"**2. Field Validation** "
                f"(Pass: {vr['summary']['pass']} | "
                f"Fail: {vr['summary']['fail']} | "
                f"Warn: {vr['summary']['warn']})"
            )
            html_val = (
                "<table style='width: 100%; border-collapse: collapse; font-size: 13px;'>"
                "<tr>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Check</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Value</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Status</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Message</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Confidence</th>"
                "</tr>"
            )
            for c in vr["checks"]:
                color = (
                    "green"
                    if c["status"] == "pass"
                    else ("orange" if c["status"] == "warn" else "red")
                )
                icon = (
                    "✅"
                    if c["status"] == "pass"
                    else ("⚠️" if c["status"] == "warn" else "❌")
                )
                conf_val = f"{(c.get('confidence', 0)*100):.1f}%" if c.get('confidence') is not None else "—"
                conf_color = "red" if c.get('confidence', 1.0) < 0.75 else ("orange" if c.get('confidence', 1.0) < 0.90 else "green")
                conf_html = f"<span style='color:{conf_color}'>{conf_val}</span>" if c.get('confidence') is not None else "—"
                
                html_val += (
                    f"<tr>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{c['check']}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{c['value']}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px;color:{color}'>"
                    f"<b>{icon} {c['status'].upper()}</b></td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{c['message']}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{conf_html}</td>"
                    f"</tr>"
                )
            html_val += "</table><br/>"
            st.markdown(html_val, unsafe_allow_html=True)

        # ── Business Rules ────────────────────────────────────────────────────
        if st.session_state.rules_report:
            rr = st.session_state.rules_report
            HIDDEN_RULES = {"PPT Format (years / monthly)", "Nominee ≠ Applicant"}
            visible_rules = [r for r in rr["rules"] if r["rule"] not in HIDDEN_RULES]

            v_pass = sum(1 for r in visible_rules if r["status"] == "pass")
            v_error = sum(1 for r in visible_rules if r["status"] == "error")
            v_warn = sum(1 for r in visible_rules if r["status"] == "warn")

            st.markdown(
                f"**3. Business Rules** "
                f"(Pass: {v_pass} | Error: {v_error} | Warn: {v_warn})"
            )
            html_rules = (
                "<table style='width: 100%; border-collapse: collapse; font-size: 13px;'>"
                "<tr>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Rule</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Status</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Message</th>"
                "<th style='text-align:left; border-bottom: 1px solid #ddd; padding: 4px;'>Code</th>"
                "</tr>"
            )
            for r in visible_rules:
                color = (
                    "green"
                    if r["status"] == "pass"
                    else ("orange" if r["status"] == "warn" else "red")
                )
                icon = (
                    "✅"
                    if r["status"] == "pass"
                    else ("⚠️" if r["status"] == "warn" else "❌")
                )
                code_html = f"<code>{r['code']}</code>" if r["code"] else ""
                html_rules += (
                    f"<tr>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{r['rule']}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px;color:{color}'>"
                    f"<b>{icon} {r['status'].upper()}</b></td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{r['message']}</td>"
                    f"<td style='border-bottom:1px solid #eee;padding:4px'>{code_html}</td>"
                    f"</tr>"
                )
            html_rules += "</table>"
            st.markdown(html_rules, unsafe_allow_html=True)
else:
    st.info("📂 Upload a document above and click **Extract Fields** to see results here.")

