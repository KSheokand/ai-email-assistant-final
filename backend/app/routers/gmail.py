# app/routers/gmail.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
import base64
import email as py_email

from ..auth_utils import refresh_credentials_if_needed
from ..ai_service import summarize_text, generate_reply_for_email

router = APIRouter()


def _gmail_service(creds):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _parse_message(msg):
    headers = msg.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}
    subject = header_map.get("subject", "(no subject)")
    sender = header_map.get("from", "")
    snippet = msg.get("snippet", "")
    body = ""

    payload = msg.get("payload", {})
    if payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    try:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                    except Exception:
                        body = data
                    break
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            try:
                body = base64.urlsafe_b64decode(data).decode("utf-8")
            except Exception:
                body = data

    return {
        "id": msg.get("id"),
        "threadId": msg.get("threadId"),
        "subject": subject,
        "from": sender,
        "snippet": snippet,
        "body": body,
    }


# app/routers/gmail.py (only the last5 endpoint shown)

@router.get("/last5")
def last5(request: Request):
    """
    Fetch and summarize the last 5 Gmail messages.
    If OpenAI quota is exceeded, summaries will say so but emails will still appear.
    """
    session = request.cookies.get("session")
    creds = refresh_credentials_if_needed(session)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = _gmail_service(creds)

    try:
        results = service.users().messages().list(
            userId="me",
            maxResults=5,
        ).execute()
        print("DEBUG /gmail/last5 list results:", results)
    except Exception as e:
        print("DEBUG /gmail/last5 list error:", e)
        raise HTTPException(status_code=500, detail=f"gmail list error: {e}")

    messages_meta = results.get("messages", [])
    if not messages_meta:
        print("DEBUG /gmail/last5: no messages returned from Gmail API")
        return JSONResponse({"messages": []})

    emails = []
    for m in messages_meta:
        try:
            full = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            print("DEBUG /gmail/last5 full message id:", m["id"])

            parsed = _parse_message(full)
            summary_source = parsed["body"] or parsed["snippet"] or ""

            # 👇 This call will now *never* raise – it returns fallback text if quota is exceeded
            parsed["summary"] = summarize_text(summary_source)

            emails.append(parsed)
        except Exception as e:
            print(
                "DEBUG /gmail/last5: failed to process message",
                m.get("id"),
                "error:",
                e,
            )
            # still append *something* so the user sees the email
            try:
                parsed_minimal = {
                    "id": m.get("id"),
                    "threadId": m.get("threadId"),
                    "subject": "(failed to parse details)",
                    "from": "",
                    "snippet": "",
                    "body": "",
                    "summary": "Failed to parse this email.",
                }
                emails.append(parsed_minimal)
            except Exception:
                continue

    print(f"DEBUG /gmail/last5: returning {len(emails)} messages")
    return JSONResponse({"messages": emails})


@router.post("/generate-reply/{message_id}")
def generate_reply(message_id: str, request: Request):
    session = request.cookies.get("session")
    creds = refresh_credentials_if_needed(session)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = _gmail_service(creds)
    full = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    parsed = _parse_message(full)

    try:
        reply = generate_reply_for_email(
            email_body=parsed["body"] or parsed["snippet"] or "",
            sender=parsed["from"],
            subject=parsed["subject"],
        )
    except Exception as e:
        print("ERROR /gmail/generate-reply:", e)
        raise HTTPException(
            status_code=429,
            detail="AI reply generation is temporarily unavailable (quota or model error).",
        )

    return JSONResponse({"reply": reply, "email": parsed})



def _build_reply_mime(original, reply_text: str, user_email: str):
    headers = original.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}
    subject = header_map.get("subject", "(no subject)")
    sender = header_map.get("from", "")
    to_addr = sender.split("<")[-1].replace(">", "").strip()

    msg = py_email.message.EmailMessage()
    msg["To"] = to_addr
    msg["From"] = user_email
    if subject.lower().startswith("re:"):
        msg["Subject"] = subject
    else:
        msg["Subject"] = "Re: " + subject
    msg["In-Reply-To"] = original.get("id")
    msg.set_content(reply_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw, "threadId": original.get("threadId")}


@router.post("/send-reply/{message_id}")
def send_reply(message_id: str, request: Request):
    data = request.json() if hasattr(request, "json") else None
    # FastAPI sync endpoint: request.json() is coroutine only in async view;
    # here we assume fastapi will parse body for us via pydantic in real code.
    # For simplicity, use body param via Request in TS frontend:
    raise HTTPException(status_code=500, detail="Use body model instead")
