# app/routers/auth.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from jose import jwt
import requests
import time
import traceback

from ..config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    BACKEND_BASE_URL,
    FRONTEND_BASE_URL,
    JWT_SECRET,
    JWT_ALG,
)
from ..db import save_token

router = APIRouter()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


@router.get("/login")
def login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=f"{BACKEND_BASE_URL}/auth/callback",
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    resp = RedirectResponse(auth_url)
    resp.set_cookie("oauth_state", state, httponly=True, samesite="lax")
    return resp


@router.get("/callback")
def callback(request: Request):
    if "error" in request.query_params:
        error = request.query_params.get("error")
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error={error}")

    state_cookie = request.cookies.get("oauth_state")
    state_param = request.query_params.get("state")
    if state_cookie and state_param and state_cookie != state_param:
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=invalid_state")

    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=no_code")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{BACKEND_BASE_URL}/auth/callback",
        "grant_type": "authorization_code",
    }

    try:
        token_resp = requests.post(token_url, data=data, timeout=10)
        token_json = token_resp.json()
    except Exception as e:
        print("Token POST failed:", e)
        traceback.print_exc()
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=token_post_failed")

    if token_resp.status_code != 200 or "access_token" not in token_json:
        print("Token endpoint error:", token_resp.status_code, token_json)
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=token_endpoint_error")

    creds = Credentials(
        token=token_json.get("access_token"),
        refresh_token=token_json.get("refresh_token"),
        token_uri=token_json.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=token_json.get("scope").split() if token_json.get("scope") else None,
    )

    try:
        uresp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10,
        )
    except Exception as e:
        print("Userinfo request failed:", e)
        traceback.print_exc()
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=userinfo_failed")

    if uresp.status_code != 200:
        print("userinfo endpoint returned:", uresp.status_code, uresp.text)
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=userinfo_failed")

    userinfo = uresp.json()
    email = userinfo.get("email")
    if not email:
        return RedirectResponse(url=f"{FRONTEND_BASE_URL}/?error=no_email")

    # save tokens
    try:
        token_entry = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "scopes": creds.scopes or [],
        }
        save_token(email, token_entry)
    except Exception as e:
        print("Failed to save token to DB:", e)
        traceback.print_exc()

    payload = {
        "sub": email,
        "email": email,
        "name": userinfo.get("name"),
        "picture": userinfo.get("picture"),
        "iat": int(time.time()),
    }
    session_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

    resp = RedirectResponse(url=f"{FRONTEND_BASE_URL}/dashboard")
    resp.set_cookie(
        "session",
        session_token,
        httponly=True,
        samesite="none",
        secure=True,  # backend on HTTPS (Render)
    )
    return resp


@router.get("/me")
def me(request: Request):
    cookie = request.cookies.get("session")
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(cookie, JWT_SECRET, algorithms=[JWT_ALG])
        return JSONResponse(
            {
                "email": payload.get("email"),
                "name": payload.get("name"),
                "picture": payload.get("picture"),
            }
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")


@router.get("/logout")
def logout():
    resp = RedirectResponse(url=f"{FRONTEND_BASE_URL}/")
    resp.delete_cookie("session", samesite="none", secure=True)
    return resp
