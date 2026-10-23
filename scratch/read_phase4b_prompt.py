import json
from pathlib import Path

transcript_path = Path(r"C:\Users\Akshitha Reddy\.gemini\antigravity-ide\brain\c4a6d059-0f12-4ec3-9728-d6b23631bc4c\.system_generated\logs\transcript.jsonl")

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("type") == "USER_INPUT":
                content = data.get("content", "")
                if "PHASE 4B — FIX ROUND" in content:
                    print("FOUND PROMPT 8:")
                    print(content)
                    break
        except Exception:
            pass
