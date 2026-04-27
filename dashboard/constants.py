# Steps and Progress mapping
STEPS = [
    ("navigate_to_sales_agent", "🧭 Navigate to Sales Agent"),
    ("extract_single_screen_data", "📋 Extract Applicant Detail"),
    ("initial_checklist_fill", "📝 Initial Checklist Fill"),
    ("navigate_to_documents", "📂 Navigate to Documents"),
    ("verify_documents", "🔍 Verify Documents"),
    ("extract_min_balance", "🏦 Analyze Bank Statement"),
    ("final_checklist_update", "✅ Final Checklist Update"),
    ("complete", "🏁 Automation Complete"),
]

PROGRESS_PCTS = [
    0.02,
    0.08,
    0.25,
    0.35,
    0.55,
    0.75,
    0.85,
    1.0,
]

DUMMY_LOG = """
[HH:MM:SS] 🚀 Starting underwriting automation agent
[HH:MM:SS] 🌐 Launching browser...
[HH:MM:SS] ✅ Browser launched (1280x900)
[HH:MM:SS] 📋 Navigating to Sales Agent app...
[HH:MM:SS] 🔍 Using VLM to visually extract data from screenshot...
[HH:MM:SS] 🤖 VLM extracted: {"first_name": "KAILASH", "pan_number": "ABCKS1234K", ...}
[HH:MM:SS] 📝 Opening Underwriting Checklist...
[HH:MM:SS] 💳 Filling PAN Validation section...
[HH:MM:SS]   ✅ Clicked YES: PAN Card Copy uploaded
[HH:MM:SS]   ✏️  Entered PAN Number: 'ABCKS1234K'
...
"""

INSURANCE_APPLICATION_EXTRACTION_PROMPT = """You are an expert OCR and data extraction assistant specialising in handwritten documents.
I am providing you with an image of a handwritten document (e.g. a form, application, or certificate). The content may be partially or fully handwritten in pen or pencil.

Your task is to extract EVERY field — printed labels AND their handwritten values — and return them all as a single flat JSON object.

Handwriting Reading Guidelines:
- Read each character carefully. Handwriting varies widely — pay close attention to letter shapes, stroke direction, and context.
- Use surrounding context (field labels, document type, adjacent words) to resolve ambiguous characters.
- If a value is partially legible, transcribe your best guess and reflect the uncertainty in the overall "extraction_confidence" score.
- Distinguish between a BLANK field (nothing written) and an ILLEGIBLE field (something written but unreadable). Return "" for both, but lower the confidence score for illegible entries.
- Do NOT invent or hallucinate values. Only transcribe what is visibly present.

Instructions:
1. Scan the entire document from top to bottom. Do not skip any section, table, box, or sidebar.
2. For each field label you find, create a JSON key derived from that label:
   - Convert the label to lowercase.
   - Replace spaces and special characters with underscores.
   - Keep the key concise but descriptive (e.g., "date_of_birth", "loan_amount_figures", "account_number").
3. For the value, capture exactly what is handwritten or filled in for that field.
4. For checkboxes or tick boxes, use a boolean: true if ticked/checked/crossed, false if empty.
5. For multi-option selections (radio buttons, tick-one-of-many), return the exact label text of the selected option as a string.
6. For tables or repeated sections (e.g., guarantors, next of kin, references), return an array of objects — one object per row.
7. Always include a special key "extraction_confidence" — a float between 0.0 and 1.0 representing your overall confidence across all handwritten values.

Rules:
1. Return ONLY a valid JSON object. Do not include markdown code blocks like ```json or any other text. Start directly with { and end with }.
2. If a field is blank or illegible, set its value to an empty string "".
3. Extract ALL fields — do not omit any field, no matter how minor.
4. Never fabricate data. Accuracy over completeness.
"""
