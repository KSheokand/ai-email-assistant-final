# app/ai.py
from typing import Optional
import textwrap
import os

from groq import Groq

from ..config import GROQ_API_KEY

# Initialize Groq client
groq_client: Optional[Groq] = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    print("WARNING: GROQ_API_KEY not set. AI features will be degraded.")


MODEL_NAME = "llama-3.1-8b-instant" # or "llama-3.1-8b-instant" if you want cheaper/faster


def _call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 256) -> str:
    """
    Small helper to call Groq chat completion.
    """
    if not groq_client:
        # Fallback if key missing
        return "AI model unavailable (missing GROQ_API_KEY)."

    try:
        resp = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print("Groq API error:", e)
        return "AI model error. Please try again later."


def summarize_email(body: str) -> str:
    """
    Summarize an email into a short, human-friendly summary (not just truncation).
    """
    body = (body or "").strip()
    if not body:
        return "No content to summarize."

    system = (
        "You are an assistant that summarizes email messages for a Gmail AI assistant. "
        "Write a short, clear, 1-2 sentence summary in plain English. "
        "Do not include greetings or signatures."
    )
    user = textwrap.dedent(
        f"""
        Please summarize the following email in 1-2 sentences:

        ---
        {body}
        ---
        """
    )

    summary = _call_groq(system, user, max_tokens=120)
    return summary


def generate_reply(subject: str, from_line: str, body: str, user_name: Optional[str] = None) -> str:
    """
    Generate a professional reply to an email using LLaMA 3.1 via Groq.
    """
    system = (
        "You are an AI email assistant. You write polite, concise, and professional email replies. "
        "Assume the user wants to respond helpfully, unless the email is spam or irrelevant."
    )

    name_part = f" The user’s name is {user_name}." if user_name else ""

    user = textwrap.dedent(
        f"""
        You are replying to this email.

        From: {from_line}
        Subject: {subject}

        Email body:
        ---
        {body}
        ---

       {name_part}

        Write a clear, professional reply that:
        - Is appropriate for the context
        - Uses a friendly but professional tone
        - Can be sent as-is from the user
        - Does NOT include a subject line (only the email body)

        Reply:
        """
    )

    reply = _call_groq(system, user, max_tokens=300)
    return reply
