# Backend test and deployment notes

## Scope used in this environment

Because Django is not available in this environment, backend test coverage was performed by **codebase examination** (test discovery + import/dependency inspection), not by executing Django test suites.

## Backend test inventory (examined)

Discovered backend test entry files:

1. `server/accounts/tests.py`
2. `server/assistant/tests.py`
3. `server/assistant/tests_mode_policy.py`
4. `server/cart/management/commands/test_cleanup.py`
5. `server/cart/management/commands/test_scoring.py`
6. `server/cart/tests.py`
7. `server/chat/tests.py`
8. `server/dashboard/tests.py`
9. `server/market/tests.py`
10. `server/notifications/tests.py`
11. `server/orders/management/commands/test_paystack.py`
12. `server/orders/tests.py`
13. `server/reviews/tests.py`
14. `server/scripts/test_answer.py`
15. `server/scripts/test_email_delivery.py`
16. `server/test_cart_task.py`

Import inspection shows 15/16 files depend on Django imports. The only file without direct Django imports is `server/assistant/tests_mode_policy.py`, but it still depends on project module resolution/runtime context.

## Potential issues in this environment

1. **Missing Django dependency**: most backend tests are Django-based and cannot run here.
2. **Python version mismatch**: `.python-version` pins `3.12.8`, while this environment provides nearby versions only.
3. **Dependency gaps**: additional packages (for example `python-decouple`) are not guaranteed to exist.
4. **Script-style tests**: some files under `server/scripts/` are CLI/integration helpers that require runtime arguments or service configuration.

## Potential issues when running full tests on another system

1. Missing PostgreSQL/Redis or unavailable service endpoints can break integration tests.
2. Missing or invalid environment variables (`.env`) can break settings import/startup paths.
3. Network-reliant scripts (email/API/paystack/Groq) may fail in CI with restricted outbound access.
4. Python patch/minor drift can change dependency resolution behavior.
5. Unapplied migrations can break model/database test cases.

## Files generally not required when testing backend for deployment

These are usually optional for backend deployment verification (unless explicitly part of release criteria):

- Frontend source/build-related files under `client/`
- User-upload/media artifacts under `static_cdn/media_root/`
- Historical narrative reports in `docs/*_COMPLETE.md`, `docs/*_REPORT.md`, and recommendation notes
- Local helper scripts not used by CI/CD (for example `verify_api.sh`)

## Documentation deduplication

- Markdown files were checked for exact duplicate content (excluding third-party `node_modules`).
- No duplicate project documentation files were found.
