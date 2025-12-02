# app/ai.py
from typing import Optional
import textwrap
import re

from groq import Groq
from ..config import GROQ_API_KEY

# ============================
# Groq client setup
# ============================

groq_client: Optional[Groq] = None
if GROQ_API_KEY:
  groq_client = Groq(api_key=GROQ_API_KEY)
else:
  print("WARNING: GROQ_API_KEY not set. AI features will be degraded.")

# Use a supported, fast model
MODEL_NAME = "llama-3.1-8b-instant"  # or "llama-3.1-70b-instant" if you want higher quality


# ============================
# Helpers
# ============================

def clean_email_body(raw: str) -> str:
  """
  Very rough cleaner:
  - Remove HTML tags
  - Collapse multiple whitespace
  """
  if not raw:
    return ""

  # Remove HTML tags
  text = re.sub(r"<[^>]+>", " ", raw)
  # Collapse whitespace
  text = re.sub(r"\s+", " ", text)
  return text.strip()


def truncate_for_model(text: str, max_chars: int = 8000) -> str:
  """
  Truncate text to a maximum number of characters.
  This is a crude but effective way to avoid huge token counts.
  """
  if not text:
    return ""
  text = text.strip()
  if len(text) <= max_chars:
    return text
  return text[:max_chars] + "\n\n[...truncated for AI processing...]"


def _call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 256) -> str:
  """
  Small helper to call Groq chat completion.
  """
  if not groq_client:
    # Fallback if key missing
    return "AI model unavailable (missing GROQ_API_KEY)."

  # Truncate the user prompt defensively as well
  user_prompt = truncate_for_model(user_prompt, max_chars=8000)

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
    print("Groq API error:", repr(e))
    # Generic graceful fallback
    return "AI model error. Please try again later."


# ============================
# Public functions
# ============================

def summarize_email(body: str) -> str:
  """
  Summarize an email into a short, human-friendly summary (not just truncation).
  We:
  - Clean HTML
  - Truncate long bodies to keep under token limits
  """
  body = clean_email_body(body or "")
  if not body:
    return "No content to summarize."

  body = truncate_for_model(body, max_chars=8000)

  system = (
    "You are an assistant that summarizes email messages for a Gmail AI assistant. "
    "Write a short, clear, 1–2 sentence summary in plain English. "
    "Do not include greetings or signatures."
  )
  user = textwrap.dedent(
    f"""
    Please summarize the following email in 1–2 sentences:

    ---
    {body}
    ---
    """
  )

  summary = _call_groq(system, user, max_tokens=120)

  # If something went wrong and we got a generic error, at least give a preview
  if summary.startswith("AI model error"):
    preview = body[:280]
    return f"AI summary unavailable. Preview: {preview}"

  return summary


def generate_reply(subject: str, from_line: str, body: str, user_name: Optional[str] = None) -> str:
  """
  Generate a professional reply to an email using LLaMA 3.1 via Groq.
  We:
  - Clean HTML
  - Truncate long threads
  """
  cleaned_body = clean_email_body(body or "")
  cleaned_body = truncate_for_model(cleaned_body, max_chars=8000)

  system = (
    "You are an AI email assistant. You write polite, concise, and professional email replies. "
    "Assume the user wants to respond helpfully, unless the email is spam or irrelevant."
  )

  name_part = f" The user's name is {user_name}." if user_name else ""

  user = textwrap.dedent(
    f"""
    You are replying to this email.

    From: {from_line}
    Subject: {subject}

    Email body:
    ---
    {cleaned_body}
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

  if reply.startswith("AI model error"):
    # Fallback: at least give the user a template instead of nothing
    return (
      "Hi,\n\n"
      "Thank you for your email. I will review the details and get back to you soon.\n\n"
      "Best regards,\n"
      f"{user_name or 'Regards'}"
    )

  return reply
