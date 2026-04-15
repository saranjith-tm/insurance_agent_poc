# Steps and Progress mapping
STEPS = [
    ("extract_applicant_data", "Extract Applicant Data from Sales App"),
    ("fill_case_details", "Fill Case Details (Card 1)"),
    ("fill_nationality", "KYC: Nationality / Resident Status"),
    ("fill_pan_validation", "KYC: PAN / PAL Validation"),
    ("fill_aadhaar_validation", "KYC: Aadhaar Validation"),
    ("fill_address_proof", "KYC: Address Proof"),
    ("fill_photo_validation", "KYC: Photo Validation"),
    ("fill_bank_validation", "KYC: Bank Account Validation"),
    ("extract_min_balance", "🔍 Find Minimum Balance from Statement"),
    ("fill_occupation", "Financial: Occupation & Industry"),
    ("fill_education", "Financial: Education Validation"),
    ("fill_nominee", "Financial: Nominee Validation"),
    ("complete", "✅ Checklist Complete"),
]

PROGRESS_PCTS = [
    0.05,
    0.15,
    0.25,
    0.32,
    0.44,
    0.54,
    0.62,
    0.72,
    0.75,
    0.82,
    0.90,
    0.96,
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
