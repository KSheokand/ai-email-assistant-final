# app/ai_service.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_text(text: str) -> str:
    """Return a short AI summary. Fall back gracefully if API fails."""
    if not text:
        return "No content to summarize."
    prompt = (
        "Summarize the following email in 1–2 concise sentences, "
        "highlighting sender intent and requested actions:\n\n"
        f"{text[:4000]}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # 👇 This is where your 429 is happening.
        print("ERROR in summarize_text:", e)
        # Fallback: at least give the user a preview instead of nothing
        preview = (text or "").strip()
        if len(preview) > 200:
            preview = preview[:200] + "..."
        return "AI summary unavailable (quota or model error). Preview: " + (
            preview or "[empty email]"
        )


def generate_reply_for_email(email_body: str, sender: str, subject: str) -> str:
    """Return a proposed reply. Raise on failure so the route can show a clear error."""
    prompt = (
        "You are a professional assistant. Write a clear, polite email reply.\n"
        "Requirements:\n"
        "- Keep it concise (120–200 words)\n"
        "- Use a professional tone\n"
        "- Refer to the subject and key points from the original email\n\n"
        f"Subject: {subject}\n"
        f"From: {sender}\n\n"
        f"Original email:\n{email_body[:4000]}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()
