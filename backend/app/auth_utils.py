# app/auth_utils.py
from typing import Optional

from fastapi import Request
from jose import jwt as jose_jwt
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from .config import JWT_SECRET, JWT_ALG
from .db import get_token


def get_session_token(request: Request) -> Optional[str]:
    """
    Get the session token from either:
    - 'session' cookie, or
    - 'Authorization: Bearer <token>' header
    """
    cookie = request.cookies.get("session")
    if cookie:
        return cookie

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def refresh_credentials_if_needed(session_token: Optional[str]) -> Optional[Credentials]:
    """
    Decode the session JWT, look up Gmail tokens in DB, and
    return google.oauth2.credentials.Credentials, or None on failure.
    """
    if not session_token:
        print("refresh_credentials_if_needed: no session token")
        return None

    try:
        payload = jose_jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception as e:
        print("refresh_credentials_if_needed decode error:", e)
        return None

    email = payload.get("email") or payload.get("sub")
    if not email:
        print("refresh_credentials_if_needed: no email in payload")
        return None

    token_entry = get_token(email)
    if not token_entry:
        print("refresh_credentials_if_needed: no token in DB for", email)
        return None

    creds = Credentials(
        token=token_entry["token"],
        refresh_token=token_entry["refresh_token"],
        token_uri=token_entry["token_uri"],
        client_id=token_entry["client_id"],
        client_secret=token_entry["client_secret"],
        scopes=token_entry["scopes"],
    )

    # Optional: refresh if expired
    if not creds.valid and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:
            print("refresh_credentials_if_needed: refresh failed", e)
            return None

    return creds
