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
