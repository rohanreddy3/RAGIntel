"""Probe candidate models for Phase 6D Part F."""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)
api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)

for m_id in ["models/gemini-3.1-flash-lite", "models/gemma-4-31b-it", "models/gemini-2.5-flash-lite"]:
    try:
        print(f"Testing {m_id}...")
        resp = client.models.generate_content(
            model=m_id,
            contents="Hello, reply with one word.",
        )
        print(f"  SUCCESS {m_id}: {resp.text.strip()}")
    except Exception as e:
        print(f"  FAILED {m_id}: {e}")
