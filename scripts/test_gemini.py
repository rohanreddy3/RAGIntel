import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY present: {bool(api_key)}, length: {len(api_key) if api_key else 0}")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.1)
    res = llm.invoke("Hello! Respond with: 'Gemini Ready'.")
    print(f"gemini-2.5-flash response: {res.content.strip()}")
except Exception as e:
    print(f"gemini-2.5-flash error: {e}")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
        res = llm.invoke("Hello! Respond with: 'Gemini Ready'.")
        print(f"gemini-2.0-flash response: {res.content.strip()}")
    except Exception as e2:
        print(f"gemini-2.0-flash error: {e2}")
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.1)
            res = llm.invoke("Hello! Respond with: 'Gemini Ready'.")
            print(f"gemini-1.5-flash response: {res.content.strip()}")
        except Exception as e3:
            print(f"gemini-1.5-flash error: {e3}")
