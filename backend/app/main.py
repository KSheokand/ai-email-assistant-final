# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, gmail, ai
from .config import FRONTEND_BASE_URL

# import db to initialize on startup
from . import db as db_module

app = FastAPI(title="AI Email Assistant - Backend")

# Allow your frontend origin(s)
origins = [
    FRONTEND_BASE_URL,
    "http://localhost:3000",
    "https://ai-email-assistant-sokq.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,     # important to allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(gmail.router, prefix="/gmail")
app.include_router(ai.router, prefix="/ai")

@app.on_event("startup")
def startup_event():
    try:
        db_module.init_db()
        print("DB initialized (tokens table ensured).")
    except Exception as e:
        print("DB init failed:", e)
