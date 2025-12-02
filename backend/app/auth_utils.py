# app/auth_utils.py

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import traceback
from jose import jwt

from .db import get_token, save_token
from .config import JWT_SECRET, JWT_ALG


def refresh_credentials_if_needed(session_cookie: str):
    try:
        if not session_cookie:
            print("DEBUG auth: no session cookie")
            return None

        payload = jwt.decode(session_cookie, JWT_SECRET, algorithms=[JWT_ALG])
        user_email = payload.get("email")
        if not user_email:
            print("DEBUG auth: no email in JWT payload", payload)
            return None

        token_data = get_token(user_email)
        if not token_data:
            print("DEBUG auth: no token_data in DB for", user_email)
            return None

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )

        try:
            if hasattr(creds, "expired") and creds.expired and creds.refresh_token:
                print("DEBUG auth: token expired, refreshing for", user_email)
                creds.refresh(Request())
                token_data["token"] = creds.token
                save_token(user_email, token_data)
        except Exception as e:
            print("DEBUG auth: refresh failed for", user_email, "error:", e)
            traceback.print_exc()
            return None

        return creds

    except Exception as e:
        print("DEBUG auth: exception during refresh_credentials_if_needed:", e)
        traceback.print_exc()
        return None
