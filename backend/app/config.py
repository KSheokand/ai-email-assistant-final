from dotenv import load_dotenv
import os

# load .env in development
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", BACKEND_BASE_URL)

JWT_SECRET = os.getenv("JWT_SECRET", "dev_jwt_secret")
JWT_ALG = os.getenv("JWT_ALGORITHM", "HS256")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# DATABASE_URL is required for Postgres token store. Example:
# postgresql://user:pass@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL")
