import json
import os
from pathlib import Path

from chatbot.common import gemini_answer

FAQ_PATH = Path(__file__).with_name("employee_faq.json")


def _load_faq():
    with open(FAQ_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _faq_answer(question):
    normalized = question.lower().strip()
    for item in _load_faq():
        faq_question = item["question"].lower()
        if normalized == faq_question or any(word in faq_question for word in normalized.split() if len(word) > 3):
            return item["answer"]
    return None


def _local_employee_answer(question):
    normalized = question.lower()
    if "teamlead" in normalized or "team lead" in normalized or "reporting manager" in normalized or "manager" in normalized:
        return "Your team lead or reporting manager will be assigned by HR during onboarding. Check your onboarding checklist or contact HR if it is not visible yet."
    if "first day" in normalized or "joining day" in normalized:
        return "On your first day, meet your reporting manager, set up your company email, complete security training, and review your onboarding checklist."
    if "laptop" in normalized or "system" in normalized:
        return "Your laptop request is handled by the onboarding workflow. If it is pending, contact HR or IT support."
    if "email" in normalized or "account" in normalized:
        return "Your company email and account setup are part of onboarding. Check your dashboard checklist for completion status."
    return None


def _has_real_gemini_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return bool(key and key != "your_gemini_api_key_here")


def answer_employee_question(question):
    question = question.strip()
    if not question:
        return "Please ask an onboarding, policy, IT support, or training question."
    local_answer = _faq_answer(question) or _local_employee_answer(question)
    if local_answer:
        return local_answer
    if _has_real_gemini_key():
        return gemini_answer(
            question,
            "You are the Employee AI Assistant for SmartHire AI. Help only with onboarding, leave, timings, dress code, IT support, training, and first-day guidance.",
        )
    return "I can help with onboarding, leave policy, office timings, dress code, IT support, training, first-day steps, team lead details, laptop requests, and account setup. Please ask one of those employee onboarding questions."
