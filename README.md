Here’s a complete `README.md` you can drop into your repo and tweak if needed 👇

---

````md
# AI Email Assistant

An AI-powered Gmail assistant that lets you:

- Sign in securely with Google OAuth
- View and summarize your latest emails
- Generate smart, context-aware replies
- Send replies via Gmail
- Delete specific emails with confirmation
- Control everything through a clean chatbot dashboard

This project is split into:

- **Backend** – FastAPI + Gmail API + OpenAI + PostgreSQL
- **Frontend** – Next.js (App Router) + Tailwind CSS

---

## 🔧 Tech Stack

**Backend**

- FastAPI
- Google OAuth2 + Gmail API
- SQLAlchemy + PostgreSQL
- JWT (session tokens)
- OpenAI API (summaries + reply generation)

**Frontend**

- Next.js (App Router, React)
- TypeScript
- Tailwind CSS
- Axios

---

## 📁 Project Structure (high level)

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── auth_utils.py
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── gmail.py
│   │       └── ai.py
│   ├── requirements.txt
│   └── .env (you create)
└── frontend/
    ├── app/
    │   ├── page.tsx          (landing / login page)
    │   └── dashboard/page.tsx
    ├── package.json
    └── .env.local           (you create)
````

---

## ✅ Prerequisites

* Node.js (LTS)
* Python 3.12+ (3.13 also works)
* PostgreSQL database (local or cloud)
* Google Cloud project with:

  * **OAuth 2.0 Client ID** (web application)
  * Gmail API enabled
* OpenAI API key (for summaries + replies)

---

# 🛠 Backend Setup (FastAPI)

`/backend`

### 1. Clone & create virtual environment

```bash
git clone https://github.com/<your-username>/ai-email-assistant.git
cd ai-email-assistant/backend

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables (`backend/.env`)

Create a `.env` file inside the `backend` folder:

```env
# URL where the backend is accessible
# Local development:
BACKEND_BASE_URL=http://localhost:8000
# Production example (Render):
# BACKEND_BASE_URL=https://your-backend.onrender.com

# URL where the frontend is accessible
# Local development:
FRONTEND_BASE_URL=http://localhost:3000
# Production example (Vercel):
# FRONTEND_BASE_URL=https://your-frontend.vercel.app

# PostgreSQL connection string
# Format: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB_NAME
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/ai_email_assistant

# Google OAuth credentials (from Google Cloud console)
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# JWT config (for session tokens)
JWT_SECRET=some-long-random-secret-string
JWT_ALGORITHM=HS256

# OpenAI API (for summarization + reply generation)
OPENAI_API_KEY=sk-...
```

> 💡 The backend automatically creates the `tokens` table on startup using SQLAlchemy, so you don’t need separate migrations for this project.

### 4. Configure Google OAuth & Gmail API

In the **Google Cloud Console**:

1. Create an **OAuth 2.0 Client ID** of type **Web application**.

2. Enable **Gmail API** for your project.

3. Set **Authorized redirect URIs**:

   * For local dev:
     `http://localhost:8000/auth/callback`
   * For production:
     `https://your-backend.onrender.com/auth/callback`

4. Copy the **Client ID** and **Client Secret** into your backend `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

The app requests these scopes:

* `openid`
* `https://www.googleapis.com/auth/userinfo.email`
* `https://www.googleapis.com/auth/userinfo.profile`
* `https://www.googleapis.com/auth/gmail.readonly`
* `https://www.googleapis.com/auth/gmail.send`
* `https://www.googleapis.com/auth/gmail.modify`

So make sure Gmail API is enabled on the same project.

### 5. Run the backend locally

From the `backend` folder:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

* [http://localhost:8000](http://localhost:8000)

Useful endpoints (for debugging):

* `GET /` → (404 by design; main app is via /docs or frontend)
* `GET /docs` → Swagger UI
* `GET /auth/login` → Starts Google OAuth flow
* `GET /auth/callback` → OAuth redirect handler (Google → backend)
* `GET /auth/me` → Returns user info if session is valid
* `GET /gmail/last5` → Last 5 emails (requires auth)
* `POST /gmail/generate-reply/{message_id}`
* `POST /gmail/send-reply/{message_id}`
* `DELETE /gmail/delete/{message_id}`

---

# 💻 Frontend Setup (Next.js + Tailwind)

`/frontend`

### 1. Install dependencies

```bash
cd ../frontend
npm install
# or
yarn
```

### 2. Configure environment variables (`frontend/.env.local`)

Create a `.env.local` file inside the `frontend` folder:

```env
# URL of your backend API
# Local development:
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Production example (Render):
# NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com
```

The frontend uses this to call the backend for:

* `/auth/login`
* `/auth/me`
* `/gmail/last5`
* `/gmail/generate-reply/...`
* `/gmail/send-reply/...`
* `/gmail/delete/...`

### 3. Run the frontend locally

```bash
npm run dev
# or
yarn dev
```

Open:

* [http://localhost:3000](http://localhost:3000)

### 4. Local login flow

1. Go to `http://localhost:3000`.

2. Click **“Login with Google”**.

3. You’ll be redirected to Google, then back to:

   ```text
   http://localhost:3000/dashboard
   ```

4. The app will:

   * Greet you by your Google profile name.
   * Explain available commands in the chatbot.
   * Let you:

     * “Show my last 5 emails”
     * “Generate reply for email 2”
     * “Send reply for email 2”
     * “Delete email 3”

---

# 🚀 Deployment Notes (Render + Vercel)

This is optional but matches the current setup.

### Backend (Render)

* Create a **Web Service** from the `backend` folder.

* Use `Python` as runtime.

* Build command (Render auto-detects usually, but you can set):

  ```bash
  pip install -r requirements.txt
  ```

* Start command:

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

* Add the same environment variables from `backend/.env` into Render’s **Environment** settings:

  * `BACKEND_BASE_URL=https://your-backend.onrender.com`
  * `FRONTEND_BASE_URL=https://your-frontend.vercel.app`
  * `DATABASE_URL=postgresql+psycopg://...`
  * `GOOGLE_CLIENT_ID=...`
  * `GOOGLE_CLIENT_SECRET=...`
  * `JWT_SECRET=...`
  * `JWT_ALGORITHM=HS256`
  * `OPENAI_API_KEY=...`

> ⚠️ Make sure `BACKEND_BASE_URL` and `FRONTEND_BASE_URL` exactly match the live URLs. If `FRONTEND_BASE_URL` is left as `http://localhost:3000`, Google login will redirect to localhost in production.

### Frontend (Vercel)

* Create a new Vercel project from the `frontend` folder.

* In Vercel → **Environment Variables**, add:

  ```env
  NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com
  ```

* Deploy.

Production login flow is then:

1. User opens `https://your-frontend.vercel.app`.
2. Clicks “Login with Google”.
3. Redirect: Frontend → Backend `/auth/login` → Google → Backend `/auth/callback`.
4. Backend sets session, then redirects to:

   ```text
   https://your-frontend.vercel.app/dashboard
   ```

---

## 🧪 Features to Test

* **Sign in with Google**

  * Works locally & in production.
* **Inbox overview**

  * Click “Refresh last 5” or ask the bot:
    `Show my last 5 emails`
* **AI summaries**

  * Each email card shows a short AI or preview summary.
* **AI reply generation**

  * Button “✨ Reply” on a card, or:
    `Generate reply for email 2`
* **Send reply**

  * Button “send” in the card, or:
    `Send reply for email 2`
* **Delete email**

  * Card button “🗑 Delete”, or:
    `Delete email 3` → confirm with `yes`.

---

## 📝 License

Add your license info here (MIT, Apache 2.0, etc.).

---

## 🙋‍♂️ Notes

* If you see `401 Unauthorized` on `/auth/me` in production:

  * Double-check `FRONTEND_BASE_URL` and `BACKEND_BASE_URL` on the backend.
  * Make sure `NEXT_PUBLIC_BACKEND_URL` on the frontend points to the same backend.
* If you see `insufficient_quota` from OpenAI, your API key is out of credits.

Happy hacking! 📨🤖
