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

INSURANCE_APPLICATION_EXTRACTION_PROMPT = """You are an expert data extraction assistant. I am providing you with an image of a 'LOAN APPLICATION FORM'.
Your task is to carefully extract all handwritten or checked fields from this document and return them as a precise JSON object.

Extract the following fields and use these exact JSON keys:
- "full_name": Applicant's full name.
- "m_no": M/NO.
- "svc_no": SVC/NO.
- "national_id_no": National ID number.
- "formation_unit": Formation/Unit.
- "mobile_no": Mobile number.
- "present_address": Present Address.
- "home_address": Home Address.
- "email": Email address.
- "is_new_loan": Boolean (true if "NEW LOAN" box is ticked, false otherwise).
- "is_top_up_loan": Boolean (true if "TOP-UP LOAN" box is ticked, false otherwise).
- "loan_type": Which loan type is ticked (e.g., "KARIBU LOAN", "EMERGENCY LOAN", "SHARIA EMERGENCY LOAN", etc. Return the exact name of the ticked box).
- "current_deposits": Current deposits amount.
- "loan_amount_words": Loan amount applied for in words.
- "loan_amount_figures": Loan amount applied for in figures.
- "purpose_of_the_loan": Purpose of the loan.
- "repayment_period_years": Repayment period in years.
- "repayment_period_months": Repayment period in months.
- "payment_mode": Which payment mode is ticked (e.g., "To Mpesa", "IFT/EFT", "RTGS").
- "mpesa_no": Mpesa number (if applicable).
- "name_of_bank": Name of bank.
- "branch": Bank branch.
- "account_name": Account name.
- "account_number": Account number.
- "signature_date": Date next to applicant's signature.
- "witness_name": Witness name.
- "witness_membership_no": Witness membership number.
- "witness_id_no": Witness ID number.
- "witness_signature_date": Date next to witness signature.
- "extraction_confidence": A float between 0.0 and 1.0 representing your confidence in reading the handwriting overall.

Rules:
1. Return ONLY a valid JSON object. Do not include markdown code blocks like ```json or any other explanatory text. Start directly with { and end with }.
2. If a text field is blank, empty, or illegible, return an empty string "".
3. Be as accurate as possible with the handwriting.
"""
