# app/routers/ai.py
from fastapi import APIRouter, HTTPException
from ..ai_service import summarize_text, generate_reply_for_email

router = APIRouter()

@router.post("/summarize")
def summarize_endpoint(payload: dict):
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return {"summary": summarize_text(text)}

@router.post("/generate_reply")
def generate_reply_endpoint(payload: dict):
    subject = payload.get("subject", "")
    sender = payload.get("sender", "Unknown")
    body = payload.get("body", "")
    return {"suggestion": generate_reply_for_email(subject, sender, body)}
