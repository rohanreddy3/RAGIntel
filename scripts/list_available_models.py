"""List available models to the Google API Key for Phase 6D Part F."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment.")
    sys.exit(1)

from google import genai

client = genai.Client(api_key=api_key)

print("Listing available models from genai.Client...")
models = list(client.models.list())
print(f"Total models returned: {len(models)}")

candidates = []
for m in models:
    name = m.name or ""
    display_name = getattr(m, "display_name", "")
    description = getattr(m, "description", "")
    supported_actions = getattr(m, "supported_actions", [])
    
    # Check if model supports generateContent
    # Filter for gemma or flash-lite, excluding gemini-3.5-flash-lite
    name_lower = name.lower()
    is_gemma = "gemma" in name_lower
    is_flash_lite = "flash-lite" in name_lower or "flash_lite" in name_lower
    is_35_flash_lite = "3.5-flash-lite" in name_lower or "3-5-flash-lite" in name_lower or "gemini-3.5-flash-lite" in name_lower

    if (is_gemma or is_flash_lite) and not is_35_flash_lite:
        candidates.append({
            "name": name,
            "display_name": display_name,
            "is_gemma": is_gemma,
            "is_flash_lite": is_flash_lite,
        })
    print(f"Model: {name} | Display: {display_name}")

print("\n" + "=" * 60)
print("CANDIDATES FOR PART F (Newest Gemma or Flash-Lite != gemini-3.5-flash-lite):")
print("=" * 60)
for c in candidates:
    print(c)
