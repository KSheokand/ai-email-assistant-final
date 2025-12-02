# app/routers/gmail.py
from typing import List, Dict, Any, Optional
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.mime.text import MIMEText

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build

from ..auth_utils import get_session_token, refresh_credentials_if_needed
from .ai import summarize_email, generate_reply

router = APIRouter()


def _get_gmail_service(request: Request):
    """
    Build an authenticated Gmail service using the session token (cookie or Authorization header).
    """
    session_token = get_session_token(request)
    creds = refresh_credentials_if_needed(session_token)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated or token invalid.")
    service = build("gmail", "v1", credentials=creds)
    return service, creds


def _get_header(headers: List[Dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_body_from_message(msg: Dict[str, Any]) -> str:
    """
    Try to extract a readable body from a Gmail message payload.
    Prefers text/plain, falls back to text/html (stripped) if needed.
    """
    payload = msg.get("payload", {})
    body = ""

    def walk_parts(part: Dict[str, Any]) -> Optional[str]:
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and ("text/plain" in mime_type or "text/html" in mime_type):
            try:
                decoded = urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
                return decoded
            except Exception:
                return None

        for sub in part.get("parts", []) or []:
            res = walk_parts(sub)
            if res:
                return res
        return None

    body = walk_parts(payload) or ""
    return body


@router.get("/last5")
def last5(request: Request):
    """
    Fetch the 5 most recent emails from the user's inbox.
    For each email, return: id, subject, from, snippet, body, and AI summary.
    """
    try:
        service, creds = _get_gmail_service(request)
    except HTTPException:
        raise
    except Exception as e:
        print("DEBUG /gmail/last5: failed to build service", e)
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service")

    try:
        list_resp = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=5)
            .execute()
        )
    except Exception as e:
        print("DEBUG /gmail/last5 list error:", e)
        raise HTTPException(status_code=500, detail="Failed to list emails")

    msgs_meta = list_resp.get("messages", []) or []

    results = []
    for meta in msgs_meta:
        msg_id = meta.get("id")
        if not msg_id:
            continue

        try:
            full = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            headers = full.get("payload", {}).get("headers", [])
            subject = _get_header(headers, "Subject") or "(no subject)"
            from_line = _get_header(headers, "From")
            snippet = full.get("snippet", "")

            body_text = _extract_body_from_message(full)

            # AI summary via Groq
            try:
                summary = summarize_email(body_text)
            except Exception as ai_err:
                print(f"DEBUG /gmail/last5: AI summarize failed for {msg_id}", ai_err)
                summary = f"AI summary unavailable. Preview: {snippet[:140]}"

            results.append(
                {
                    "id": msg_id,
                    "subject": subject,
                    "from": from_line,
                    "snippet": snippet,
                    "body": body_text,
                    "summary": summary,
                }
            )

        except Exception as e:
            print(f"DEBUG /gmail/last5: failed to parse message {msg_id}", e)
            continue

    return {"messages": results}


@router.post("/generate-reply/{message_id}")
def generate_reply_for_message(message_id: str, request: Request):
    """
    Generate a proposed reply (AI) for a given email message ID.
    """
    try:
        service, creds = _get_gmail_service(request)
    except HTTPException:
        raise
    except Exception as e:
        print("DEBUG /gmail/generate-reply: failed to build service", e)
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service")

    try:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except Exception as e:
        print("DEBUG /gmail/generate-reply get message error:", e)
        raise HTTPException(status_code=404, detail="Email not found")

    headers = full.get("payload", {}).get("headers", [])
    subject = _get_header(headers, "Subject") or "(no subject)"
    from_line = _get_header(headers, "From")
    body_text = _extract_body_from_message(full)

    # Generate reply using Groq
    try:
        reply_text = generate_reply(subject, from_line, body_text)
    except Exception as e:
        print("ERROR /gmail/generate-reply AI error:", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate AI reply. Please try again later.",
        )

    return {"reply": reply_text}


@router.post("/send-reply/{message_id}")
def send_reply(message_id: str, request: Request, payload: Dict[str, str]):
    """
    Send a reply via Gmail for a given message, using the reply text from the client.
    """
    reply_text = payload.get("reply_text")
    if not reply_text:
        raise HTTPException(status_code=400, detail="Missing reply_text")

    try:
        service, creds = _get_gmail_service(request)
    except HTTPException:
        raise
    except Exception as e:
        print("DEBUG /gmail/send-reply: failed to build service", e)
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service")

    try:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except Exception as e:
        print("DEBUG /gmail/send-reply get message error:", e)
        raise HTTPException(status_code=404, detail="Email not found")

    headers = full.get("payload", {}).get("headers", [])
    subject = _get_header(headers, "Subject") or "(no subject)"
    from_line = _get_header(headers, "From")
    # Extract the actual email address from From:
    to_addr = from_line

    # Build MIME message
    mime_msg = MIMEText(reply_text)
    mime_msg["To"] = to_addr
    mime_msg["Subject"] = f"Re: {subject}"

    raw = urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

    try:
        send_resp = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw, "threadId": full.get("threadId")})
            .execute()
        )
        print("DEBUG /gmail/send-reply sent:", send_resp.get("id"))
    except Exception as e:
        print("DEBUG /gmail/send-reply send error:", e)
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"status": "sent"}


@router.delete("/delete/{message_id}")
def delete_message(message_id: str, request: Request):
    """
    Delete an email message from the user's inbox.
    """
    try:
        service, creds = _get_gmail_service(request)
    except HTTPException:
        raise
    except Exception as e:
        print("DEBUG /gmail/delete: failed to build service", e)
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service")

    try:
        service.users().messages().delete(userId="me", id=message_id).execute()
    except Exception as e:
        print("DEBUG /gmail/delete error:", e)
        raise HTTPException(status_code=500, detail="Failed to delete email")

    return {"status": "deleted"}
