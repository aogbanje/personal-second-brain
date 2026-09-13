import os
from dotenv import load_dotenv

load_dotenv()

# Secure parsing with automated text sanitization
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "xkiro").strip().lower()
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db").strip()
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "personal-second-brain").strip()

# Target parameters clean formatting
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY", "").strip()
XKIRO_BASE_URL = os.getenv("XKIRO_BASE_URL", "https://xkiro.com").strip()
XKIRO_MODEL = os.getenv("XKIRO_MODEL", "openai/gpt-4o-mini").strip()
