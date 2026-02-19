# New Machine Setup & Test Checklist (Zunto)

Use this checklist when someone clones the repo on another laptop/PC and wants to run tests without reading source code.

## 1) Confirm system prerequisites

- **Git** installed
- **Node.js 20+** and npm available
- **Python 3.12.8** available (or compatible pyenv setup)
- **pip** available

Quick checks:

```bash
git --version
node -v
npm -v
python --version
pip --version
```

---

## 2) Clone and enter project

```bash
git clone <your-repo-url>
cd Zunto
```

---

## 3) Create backend environment file

Create `server/.env` using `server/.env.example` as template:

```bash
cp server/.env.example server/.env
```

Fill in values for the following **required titles**:

### Runtime
- `RENDER`
- `DEBUG`
- `SECRET_KEY`
- `FRONTEND_URL`

### Database / Cache / Async
- `DATABASE_URL`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_URL`

### Email
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `ADMIN_EMAIL`
- `EMAIL_USE_CONSOLE_IN_DEBUG`

### Payments
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`

### AI / Assistant
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_TIMEOUT_SECONDS`
- `GROQ_BULKHEAD_LIMIT`
- `GROQ_RATE_LIMIT_COOLDOWN_SECONDS`
- `LLM_MAX_PROMPT_TOKENS`
- `LLM_MAX_OUTPUT_TOKENS`
- `FAQ_MATCH_THRESHOLD`
- `SENTENCE_TRANSFORMER_MODEL`
- `PHASE1_UNIFIED_CONFIDENCE`
- `PHASE1_CONTEXT_INTEGRATION`
- `PHASE1_INTENT_CACHING`
- `PHASE1_LLM_CONTEXT_ENRICHMENT`
- `PHASE1_RESPONSE_PERSONALIZATION_FIX`
- `CHAT_HMAC_SECRET`

### Auth
- `GOOGLE_OAUTH_CLIENT_ID`

> Minimum local run can work with some defaults, but for full feature testing these should be set correctly.

---

## 4) Create frontend environment file

Create `client/.env.local` (or `.env`) using `client/.env.example` titles:

```bash
cp client/.env.example client/.env.local
```

Set at least:

- `VITE_API_BASE` (recommended canonical key, e.g. `http://localhost:8000`)
- `VITE_GOOGLE_CLIENT_ID`

Optional aliases (legacy compatibility):
- `VITE_API_BASE_URL`
- `VITE_API_URL`

---

## 5) Install backend dependencies

```bash
cd server
python -m venv venv
source venv/bin/activate   # Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

Optional:

```bash
python manage.py createsuperuser
```

---

## 6) Install frontend dependencies

Open a second terminal:

```bash
cd client
npm install
```

---

## 7) Start both services

Backend terminal:

```bash
cd server
source venv/bin/activate   # Windows PowerShell: .\venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000
```

Frontend terminal:

```bash
cd client
npm run dev
```

Expected URLs:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Health: `http://localhost:8000/health/`

---

## 8) Smoke tests to confirm clone works

### Backend checks

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/api/market/categories/
```

### Frontend checks
- Open signup page and confirm:
  - Register button is disabled/faded initially
  - It stays disabled until all required fields + terms/privacy checkbox are completed

### Build & lint checks

```bash
cd client
npm run lint
npm run build
```

---

## 9) Common missing items on new machines

If clone fails, usually one of these is missing:

- Python version mismatch with `.python-version` (3.12.8)
- Missing `.env` / `.env.local` values
- Redis/Postgres not available while env points to them
- Required API keys not present for Google/Paystack/Groq features
- Dependencies not installed (`pip install -r requirements.txt`, `npm install`)

---

## 10) Fast “ready for tester” confirmation

Before handing to any tester, confirm all below are true:

- [ ] `server/.env` exists with valid values
- [ ] `client/.env.local` exists with API base URL + Google client ID
- [ ] Django migrations completed successfully
- [ ] Backend returns `{"status":"ok"}` at `/health/`
- [ ] Frontend loads at `localhost:5173`
- [ ] `npm run lint` and `npm run build` pass
- [ ] Signup consent checkbox behavior works as expected
