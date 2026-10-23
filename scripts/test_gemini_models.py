import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY present: {bool(api_key)}, length: {len(api_key) if api_key else 0}")

client = genai.Client(api_key=api_key)

candidate_models = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-flash-latest"
]

selected_model = None
for model_name in candidate_models:
    print(f"\nTesting generation with '{model_name}'...")
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, please respond with the word SUCCESS only.",
            )
            print(f"--> [OK] {model_name}: {response.text.strip()}")
            selected_model = model_name
            break
        except Exception as e:
            print(f"--> [Attempt {attempt+1} Failed] {model_name}: {e}")
            time.sleep(2)
    if selected_model:
        break

print(f"\nSelected working Gemini model: {selected_model}")
