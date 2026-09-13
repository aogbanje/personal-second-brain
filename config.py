import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "xkiro").lower()
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "personal-second-brain")

# xKiro Specific Parameters
XKIRO_API_KEY = os.getenv("XKIRO_API_KEY")
XKIRO_BASE_URL = os.getenv("XKIRO_BASE_URL", "https://xkiro.com")
XKIRO_MODEL = os.getenv("XKIRO_MODEL", "gpt-4o-mini")
