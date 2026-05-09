# Zunto Render Deployment Notes

## Render Blueprint

Use the root-level `render.yaml`. The older `server/render.yaml` is deprecated because Render auto-detects Blueprints from the repository root.

The Blueprint defines:

- `zunto-backend`: Django ASGI backend served by Daphne for HTTP and WebSocket traffic.
- `zunto-frontend`: Vite static site built from `client` and published from `client/dist`.
- `zunto-db`: Render PostgreSQL on the free plan.

Render's PostgreSQL extension documentation lists `pgvector` for PostgreSQL 13 and later and enables it with `CREATE EXTENSION vector;`. The Zunto migrations already attempt `CREATE EXTENSION IF NOT EXISTS vector`, so the free PostgreSQL database can support the vector-search architecture as long as it is created on PostgreSQL 13 or newer. The Blueprint pins PostgreSQL 16.

## WebSockets and Redis

The free-tier Blueprint intentionally does not create a Redis/Key Value service. In that mode, production settings use Django Channels' in-memory channel layer so marketplace chat can work during the single-instance investor demo.

This is not the final production architecture. Before scaling beyond one backend instance, add a Render Key Value/Redis service, set `REDIS_URL`, switch Channels back to `channels_redis`, and run dedicated Celery worker/beat services for background jobs.

## Media Files

Render free instances do not provide persistent app filesystem storage. Seller-uploaded product images, videos, dispute evidence, and other media written to `MEDIA_ROOT` can disappear after restarts or redeploys.

Seeded demo products use external image URLs, so the investor demo catalog is safe. For production, add one of:

- A paid Render persistent disk mounted at the media directory.
- Object storage such as S3, Cloudinary, or another Django storage backend.

Do not rely on the free-tier filesystem for seller uploads.

## Required Render Environment Variables

Set these on the relevant Render service before deploying. The root Blueprint sets several automatically; variables marked `sync: false` must be filled in the Dashboard.

| Variable | Service | What it does | Secret | Safe example |
| --- | --- | --- | --- | --- |
| `PYTHON_VERSION` | Backend | Pins the Python runtime. | No | `3.12.8` |
| `PRODUCTION` | Backend | Forces production-safe settings. | No | `True` |
| `RENDER_FREE_TIER` | Backend | Enables free-tier memory/runtime fallbacks. | No | `True` |
| `SECRET_KEY` | Backend | Django cryptographic signing key. | Yes | Generate in Render |
| `BACKEND_URL` | Backend | Public backend URL used to derive `ALLOWED_HOSTS`. | No | `https://zunto-backend.onrender.com` |
| `ALLOWED_HOSTS` | Backend | Extra comma-separated hostnames accepted by Django. | No | `zunto-backend.onrender.com` |
| `FRONTEND_URL` | Backend | Public frontend origin for links and CORS defaults. | No | `https://zunto-frontend.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | Backend | Comma-separated browser origins allowed to call the API. | No | `https://zunto-frontend.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | Backend | Origins trusted for cross-site CSRF-protected requests. | No | `https://zunto-frontend.onrender.com` |
| `DATABASE_URL` | Backend | PostgreSQL connection string injected from `zunto-db`. | Yes | Render database reference |
| `GROQ_API_KEY` | Backend | Enables AI assistant responses through Groq. | Yes | `gsk_xxx` |
| `CHAT_HMAC_SECRET` | Backend | Signs marketplace chat WebSocket tokens. | Yes | Generate in Render |
| `PAYSTACK_SECRET_KEY` | Backend | Server-side Paystack payment verification. | Yes | `sk_test_xxx` |
| `PAYSTACK_PUBLIC_KEY` | Backend | Public Paystack checkout key. | No | `pk_test_xxx` |
| `PAYSTACK_WEBHOOK_SECRET` | Backend | Verifies Paystack webhook signatures. | Yes | `whsec_or_paystack_secret` |
| `EMAIL_HOST_USER` | Backend | SMTP username for signup/password/reset emails. | Yes | `demo@zunto.ng` |
| `EMAIL_HOST_PASSWORD` | Backend | SMTP password or app password. | Yes | `app-password-value` |
| `DEFAULT_FROM_EMAIL` | Backend | From address for outbound email. | No | `Zunto <noreply@zunto.ng>` |
| `GOOGLE_OAUTH_CLIENT_ID` | Backend | Backend Google token audience/client ID. | No | `123.apps.googleusercontent.com` |
| `PRODUCT_VECTOR_BACKEND` | Backend | Chooses vector backend; `auto` uses pgvector when ready. | No | `auto` |
| `VITE_API_BASE_URL` | Frontend | Build-time API base URL for all frontend API/WebSocket calls. | No | `https://zunto-backend.onrender.com` |
| `VITE_GOOGLE_CLIENT_ID` | Frontend | Build-time Google OAuth browser client ID. | No | `123.apps.googleusercontent.com` |

Render also injects `RENDER`, `RENDER_EXTERNAL_URL`, and `RENDER_EXTERNAL_HOSTNAME` automatically for web services and static sites. The backend uses these as safety nets, but keep `BACKEND_URL`, `FRONTEND_URL`, and the CORS/CSRF values explicit so the Dashboard is easy to audit.

## Optional Backend Variables With Defaults

These are read by `settings.py` or related server code. Set them only if you need to override the defaults.

| Variable | What it does | Secret | Safe example |
| --- | --- | --- | --- |
| `DEBUG` | Local development debug flag; ignored when `PRODUCTION=True`. | No | `False` |
| `REDIS_URL` | Enables Redis cache, Channels, and async Celery when a Redis service exists. | Yes | `redis://red-xxx:6379` |
| `REDIS_HOST` | Local Redis hostname fallback. | No | `localhost` |
| `REDIS_PORT` | Local Redis port fallback. | No | `6379` |
| `EMAIL_BACKEND` | Django email backend. | No | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP host. | No | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port. | No | `587` |
| `EMAIL_USE_TLS` | SMTP TLS toggle. | No | `True` |
| `ADMIN_EMAIL` | Administrative contact email. | No | `admin@zunto.ng` |
| `EMAIL_USE_CONSOLE_IN_DEBUG` | Prints email locally when debugging. | No | `False` |
| `PAYMENT_ALLOWED_CALLBACK_HOSTS` | Comma-separated safe callback hostnames for payment return URLs. | No | `zunto-frontend.onrender.com` |
| `GROQ_MODEL` | Groq model name. | No | `llama-3.3-70b-versatile` |
| `GROQ_TIMEOUT_SECONDS` | Groq request timeout. | No | `8` |
| `GROQ_BULKHEAD_LIMIT` | Max concurrent Groq calls when not on free tier. | No | `16` |
| `GROQ_RATE_LIMIT_COOLDOWN_SECONDS` | Cooldown after Groq rate limiting. | No | `30` |
| `LLM_MAX_PROMPT_TOKENS` | Assistant prompt token cap. | No | `900` |
| `LLM_MAX_OUTPUT_TOKENS` | Assistant output token cap. | No | `500` |
| `FAQ_MATCH_THRESHOLD` | FAQ similarity threshold. | No | `0.5` |
| `EMBEDDING_MODEL` | Sentence embedding model name. | No | `all-MiniLM-L12-v2` |
| `PRODUCT_VECTOR_DIMENSIONS` | Product embedding dimensions. | No | `384` |
| `PRODUCT_VECTOR_TABLE` | Override pgvector table name. | No | `market_product_vector` |
| `PRODUCT_RECOMMENDER_CANDIDATE_LIMIT` | Candidate cap when not on free tier. | No | `1000` |
| `HOMEPAGE_RECO_SESSION_TTL_MINUTES` | Homepage recommendation session TTL. | No | `20` |
| `ASSISTANT_PRELOAD_DATA` | Preloads assistant data when memory budget allows. | No | `False` |
| `AI_COMPONENTS_DISABLED` | Disables AI components for tests or emergency fallback. | No | `False` |
| `RECO_FEED_CATEGORY_WEIGHT` | Recommendation category weight. | No | `1.15` |
| `RECO_FEED_BUDGET_WEIGHT` | Recommendation budget weight. | No | `1.1` |
| `RECO_BEHAVIOR_AGGREGATION_MINUTES` | Behavior aggregation window. | No | `15` |
| `PHASE1_UNIFIED_CONFIDENCE` | Assistant feature toggle. | No | `True` |
| `PHASE1_CONTEXT_INTEGRATION` | Assistant feature toggle. | No | `True` |
| `PHASE1_INTENT_CACHING` | Assistant feature toggle. | No | `True` |
| `PHASE1_LLM_CONTEXT_ENRICHMENT` | Assistant feature toggle. | No | `True` |
| `PHASE1_RESPONSE_PERSONALIZATION_FIX` | Assistant feature toggle. | No | `True` |
| `CHAT_BLOCKED_LINK_DOMAINS` | Comma-separated blocked domains in chat. | No | `grabify.link,bit.ly,tinyurl.com` |
| `MALWARE_SCAN_ENABLED` | Enables upload malware scanning. | No | `False` |
| `MALWARE_SCAN_BACKEND` | Malware scanning backend. | No | `clamav` |
| `MALWARE_SCAN_FAIL_CLOSED` | Blocks uploads if scanning fails. | No | `False` |
| `MALWARE_SCAN_CLAMAV_HOST` | ClamAV hostname. | No | `127.0.0.1` |
| `MALWARE_SCAN_CLAMAV_PORT` | ClamAV port. | No | `3310` |
| `MALWARE_SCAN_TIMEOUT_SECONDS` | Malware scanner timeout. | No | `5` |
| `MALWARE_QUARANTINE_ON_DETECT` | Stores detected files in quarantine. | No | `True` |
| `MALWARE_QUARANTINE_DIR` | Quarantine directory override. | No | `/tmp/zunto-quarantine` |
| `SLOW_REQUEST_THRESHOLD_MS` | Slow request logging threshold. | No | `1500` |
| `HEALTH_ALERT_ACTIVE_TASKS_THRESHOLD` | Celery active-task alert threshold. | No | `100` |
| `HEALTH_ALERT_SCHEDULED_TASKS_THRESHOLD` | Celery scheduled-task alert threshold. | No | `200` |
| `HEALTH_ALERT_RESERVED_TASKS_THRESHOLD` | Celery reserved-task alert threshold. | No | `100` |
| `HEALTH_ALERT_REDIS_QUEUE_DEPTH_THRESHOLD` | Redis queue depth alert threshold. | No | `500` |
| `HEALTH_ALERT_NOTIFY_EMAIL_ENABLED` | Sends health alerts by email. | No | `False` |
| `HEALTH_ALERT_NOTIFY_EMAIL_COOLDOWN_SECONDS` | Email alert cooldown. | No | `900` |
| `HEALTH_ALERT_RECIPIENTS` | Comma-separated health alert emails. | No | `ops@zunto.ng` |
| `HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED` | Sends health alerts to a webhook. | No | `False` |
| `HEALTH_ALERT_WEBHOOK_URL` | Health alert webhook URL. | Yes | `https://hooks.example.com/services/...` |
| `HEALTH_ALERT_NOTIFY_WEBHOOK_COOLDOWN_SECONDS` | Webhook alert cooldown. | No | `300` |
| `HEALTH_REDIS_QUEUE_NAMES` | Redis/Celery queue names for health checks. | No | `celery` |
| `PUBLIC_MEDIA_BASE_URL` | Absolute media URL base when serving media externally. | No | `https://cdn.zunto.ng` |
| `SITE_URL` | Site URL fallback for media URL generation. | No | `https://zunto-frontend.onrender.com` |

## Optional Frontend Build Variables

| Variable | What it does | Secret | Safe example |
| --- | --- | --- | --- |
| `VITE_API_BASE` | Legacy alias for the API base URL. Prefer `VITE_API_BASE_URL`. | No | `https://zunto-backend.onrender.com` |
| `VITE_API_URL` | Legacy alias for the API base URL. Prefer `VITE_API_BASE_URL`. | No | `https://zunto-backend.onrender.com` |

## Dashboard Checklist

1. Push the root `render.yaml` to the connected Git repository.
2. In Render, open **Blueprints** and create/apply a Blueprint from the repo.
3. Fill every `sync: false` value shown by the Blueprint, especially `GROQ_API_KEY`, Paystack keys, email credentials, and Google OAuth client IDs.
4. Confirm the backend service environment has `BACKEND_URL`, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` matching the actual Render service URLs.
5. After deploy, open the PostgreSQL database shell and verify `CREATE EXTENSION vector;` is available if migrations did not already create it.
6. Redeploy the frontend if `VITE_API_BASE_URL` or `VITE_GOOGLE_CLIENT_ID` changes, because Vite reads them at build time.
