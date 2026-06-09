import os

from config import load_env_file

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def gemini_answer(question, persona):
    load_env_file()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or genai is None:
        return "I could not find this locally. Add GEMINI_API_KEY to enable Gemini fallback."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"{persona}\nAnswer concisely.\nQuestion: {question}")
    return response.text
