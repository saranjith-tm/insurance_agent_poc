import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SALES_AGENT_PORT = 5001
UNDERWRITING_PORT = 5002
DASHBOARD_PORT = 8501

SALES_AGENT_URL = f"http://localhost:{SALES_AGENT_PORT}"
UNDERWRITING_URL = f"http://localhost:{UNDERWRITING_PORT}"

# Default API keys (can be overridden via dashboard or environment)
DEFAULT_OPENROUTER_KEY = os.getenv(
    "OPENROUTER_API_KEY", ""
)

# VLM Model configurations
VLM_MODELS = {
    "OpenRouter - Qwen2.5-VL-32B (Recommended)": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-32b-instruct",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "OpenRouter - Qwen2.5-VL-72B": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-72b-instruct",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "OpenRouter - Qwen2.5-VL-7B (Fast)": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-7b-instruct",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "OpenRouter - Pixtral 12B (Free)": {
        "provider": "openrouter",
        "model_id": "mistralai/pixtral-12b",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "Anthropic - Claude 3.5 Sonnet": {
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "api_base": None,
    },
    "OpenAI - GPT-4o": {
        "provider": "openai",
        "model_id": "gpt-4o",
        "api_base": "https://api.openai.com/v1",
    },
    "Google - Gemini 1.5 Pro": {
        "provider": "google",
        "model_id": "gemini-1.5-pro",
        "api_base": None,
    },
}

# Dummy applicant data
APPLICANT_DATA = {
    "application_no": "OS121345678",
    "case_type": "AMR",
    "name": "Kailash Suresh",
    "first_name": "KAILASH",
    "last_name": "SURESH",
    "dob": "15/03/1985",
    "age": 41,
    "gender": "Male",
    "marital_status": "Single",
    "nationality": "Indian",
    "resident_status": "NRI",
    "pan_no": "ABCKS1234K",
    "aadhaar_no": "1234 5678 9012",
    "mobile": "+91-9886122211",
    "email": "kailash.suresh@email.com",
    "address1": "NO 10 11TH STREET TANSI NAGAR",
    "address2": "",
    "city": "Chennai",
    "state": "Tamil Nadu",
    "pincode": "600017",
    "country": "Sweden",
    "occupation": "Salaried",
    "organisation_type": "PRIVATE LTD",
    "industry": "IT/Software",
    "education": "Graduate",
    "annual_income": 6000000,
    "experian_income": 300000,
    "politically_exposed": "No",
    "high_risk": "No",
    "bank_account": "12345678901234",
    "bank_name": "HDFC Bank",
    "ifsc": "HDFC0001234",
    "nominee_name": "Priya Suresh",
    "nominee_relation": "Wife",
    "plan": "UW3 - Term Life Insurance",
    "product_code": "UW3",
    "sum_assured": 4500000,
    "premium": 50000,
    "sourcing_type": "FR",
    "advisor_code": "R1530734",
}
