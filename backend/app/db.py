# app/db.py
"""
Postgres-backed token store for AI Email Assistant.
Uses SQLAlchemy core to create a simple tokens table:
  tokens(email text primary key, data text)

Functions:
- init_db()
- save_token(email, token_dict)
- get_token(email) -> token_dict or None
"""

import os
import json
from sqlalchemy import create_engine, Table, Column, String, Text, MetaData, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from .config import DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Set it in .env or environment variables.")

# create engine
engine = create_engine(DATABASE_URL, future=True)
meta = MetaData()

tokens_table = Table(
    "tokens",
    meta,
    Column("email", String, primary_key=True),
    Column("data", Text, nullable=False),
)

def init_db():
    """Create tokens table if missing."""
    meta.create_all(engine)

def save_token(email: str, token_dict: dict):
    """Upsert token JSON for email."""
    if not email:
        raise ValueError("email required")
    payload = json.dumps(token_dict)
    stmt = pg_insert(tokens_table).values(email=email, data=payload)
    stmt = stmt.on_conflict_do_update(index_elements=["email"], set_={"data": stmt.excluded.data})
    try:
        with engine.begin() as conn:
            conn.execute(stmt)
    except SQLAlchemyError as e:
        print("DB save_token error:", e)
        raise

def get_token(email: str):
    """Return parsed token dict or None."""
    if not email:
        return None
    stmt = select(tokens_table.c.data).where(tokens_table.c.email == email)
    try:
        with engine.connect() as conn:
            res = conn.execute(stmt).fetchone()
            if not res:
                return None
            return json.loads(res[0])
    except SQLAlchemyError as e:
        print("DB get_token error:", e)
        return None
