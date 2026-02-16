# Backend ↔ Frontend Integration Review (Accounts, Products/Market, Chat, Assistant)

## Scope and method
- Backend scope reviewed:
  - `server/accounts/views.py` + `server/accounts/urls.py`
  - `server/market/views.py` + `server/market/urls.py` (used as products module)
  - `server/chat/views.py` + `server/chat/urls.py` + websocket stack in `server/chat/routing.py` and `server/chat/consumers.py`
  - `server/assistant/views.py` + `server/assistant/urls.py` + `server/assistant/processors/conversation_manager.py`
- Frontend scope reviewed:
  - `client/src/services/api.js`
  - React pages/components/contexts that invoke the API layer

---

## Step 1 — Backend endpoint verification + React coverage

## 1) Accounts module

| Module | Endpoint | Method(s) | Permissions/Auth | React coverage | Notes |
|---|---|---|---|---|---|
| accounts | `/api/accounts/register/` | POST | Public (`AllowAny`) + ratelimit | ✅ | Used in `AuthContext.register`. |
| accounts | `/api/accounts/register/verify/` | POST | Public (`AllowAny`) + ratelimit | ✅ | Used in `AuthContext.verifyRegistration`. |
| accounts | `/api/accounts/register/resend/` | POST | Public (`AllowAny`) + ratelimit | ✅ | Used in `AuthContext.resendRegistrationCode`. |
| accounts | `/api/accounts/login/` | POST | Public (JWT token obtain view) + ratelimit | ✅ | Used in `AuthContext.login`. |
| accounts | `/api/accounts/logout/` | POST | Authenticated (`IsAuthenticated`) | ✅ | Used in `AuthContext.logout`. |
| accounts | `/api/accounts/auth/google/` | POST | Public (`AllowAny`) + ratelimit | ✅ | Used by `GoogleAuthButton` via axios. |
| accounts | `/api/accounts/token/refresh/` | POST | Public (JWT refresh) | ⚠️ Partial | API function exists; no automatic refresh workflow in auth context/interceptor. |
| accounts | `/api/accounts/profile/` | GET/PUT/PATCH | Authenticated (`IsAuthenticated`) | ✅ | `getUserProfile` used. Update API exists but no strong profile editing flow parity checked here. |
| accounts | `/api/accounts/change-password/` | POST | Authenticated (`IsAuthenticated`) | ❌ | API exists; not wired from visible profile UI flow. |
| accounts | `/api/accounts/verify-email/` | POST | Authenticated (`IsAuthenticated`) | ❌ | API exists; no clear React flow wired. |
| accounts | `/api/accounts/resend-verification/` | POST | Authenticated (`IsAuthenticated`) | ❌ | API exists; no clear React flow wired. |
| accounts | `/api/accounts/password-reset/request/` | POST | Public (`AllowAny`) + ratelimit | ❌ | API exists but no password reset page/workflow found. |
| accounts | `/api/accounts/password-reset/confirm/` | POST | Public (`AllowAny`) | ❌ | API exists but no reset confirm page/workflow found. |
| accounts | `/accounts/login_page/`, `/accounts/register-page/` | GET | Public HTML pages | ❌ (N/A for SPA) | Legacy/server-rendered pages, not used by React SPA. |

### Accounts findings
- OAuth/session-related endpoint exists and is integrated (`auth/google`).
- JWT refresh endpoint exists but frontend lacks robust refresh-on-401 strategy.
- Several auth lifecycle endpoints are exposed but not surfaced in UX (password reset, email verification, change password).

---

## 2) Products module (implemented as `market`)

| Module | Endpoint | Method(s) | Permissions/Auth | React coverage | Notes |
|---|---|---|---|---|---|
| products/market | `/api/market/categories/` | GET | Public (`AllowAny`) | ✅ | Used on home/shop. |
| products/market | `/api/market/locations/` | GET | Public (`AllowAny`) | ❌ | API exists but no clear UI usage found. |
| products/market | `/api/market/products/` | GET/POST | Read public, create authenticated (`IsAuthenticatedOrReadOnly`) | ✅ Partial | GET used heavily; create path exists in API layer but no complete create-product UI verified in this review. |
| products/market | `/api/market/products/my-products/` | GET | Authenticated | ✅ | Used in profile/reviews flows. |
| products/market | `/api/market/products/featured/` | GET | Public | ⚠️ Partial | API exists, but Home uses generic products endpoint with `featured=true` query; backend does not explicitly filter `featured` query param in view. |
| products/market | `/api/market/products/boosted/` | GET | Public | ❌ | No usage found. |
| products/market | `/api/market/products/<slug>/` | GET/PUT/PATCH/DELETE | Read public, write seller-only (`IsSellerOrReadOnly`) | ✅ Partial | GET used in ProductDetail; write methods present in API layer but not fully surfaced in UX. |
| products/market | `/api/market/products/<slug>/similar/` | GET | Public | ❌ | API exists but no frontend call usage found. |
| products/market | `/api/market/products/<slug>/stats/` | GET | Authenticated seller-owned product only | ❌ | API exists but no seller analytics wiring found. |
| products/market | `/api/market/products/<slug>/mark-sold/` | POST | Authenticated seller-owned product only | ❌ | Not wired in frontend. |
| products/market | `/api/market/products/<slug>/reactivate/` | POST | Authenticated seller-owned product only | ❌ | Not wired in frontend. |
| products/market | `/api/market/products/<slug>/images/` | POST | Authenticated seller-owned product only | ❌ | API helper exists; no complete media management UI found. |
| products/market | `/api/market/products/<slug>/images/<image_id>/` | DELETE | Authenticated seller-owned product only | ❌ | Same as above. |
| products/market | `/api/market/products/<slug>/videos/` | POST | Authenticated seller-owned product only | ❌ | Same as above. |
| products/market | `/api/market/products/<slug>/favorite/` | POST | Authenticated | ✅ | Wired in product detail and product card interactions. |
| products/market | `/api/market/favorites/` | GET | Authenticated | ❌ | No dedicated favorites page integration found. |
| products/market | `/api/market/products/<slug>/report/` | POST | Authenticated | ❌ | No report UI integration found. |

### Product sharing/security (specific checks)
- Product identity is stable and shareable by unique slug (`slug` is unique DB field and generated uniquely). ✅
- `shares_count` exists, but there is **no dedicated share endpoint/policy enforcement** in current market views. ❌
- Required business rules from objective are **not implemented** as explicit permissions:
  - Buyer can share products they viewed.
  - Seller can share only own products.
  - Nobody can share others’ products.
- Recommendation: add explicit share action endpoint with role and ownership checks and immutable share audit log.

---

## 3) Chat module (marketplace messaging)

| Module | Endpoint | Method(s) | Permissions/Auth | React coverage | Notes |
|---|---|---|---|---|---|
| chat | `/chat/conversations/` | GET/POST/PUT/PATCH/DELETE (viewset) | Authenticated | ✅ Partial | React fetches list, but create/get_or_create action flow not wired in UI. |
| chat | `/chat/conversations/get_or_create/` | POST (custom action) | Authenticated | ❌ | Core buyer→seller initiation endpoint not used from product views. |
| chat | `/chat/conversations/<id>/messages/` | GET (custom action) | Authenticated participant-only | ❌ | React currently requests `/chat/messages/?conversation=...` instead. |
| chat | `/chat/conversations/<id>/mark_as_read/` | POST (custom action) | Authenticated participant-only | ❌ | Not wired. |
| chat | `/chat/conversations/<id>/confirm_sale/` | POST | Seller only for that conversation | ❌ | Not wired. |
| chat | `/chat/conversations/<id>/confirm_receipt/` | POST | Buyer only for that conversation | ❌ | Not wired. |
| chat | `/chat/conversations/<id>/transaction_status/` | GET | Participant-only | ❌ | Not wired. |
| chat | `/chat/messages/` | GET/POST/DELETE | Authenticated participant-scoped queryset | ✅ Partial | POST used. GET used but likely mismatched behavior/expectation. |
| chat (websocket) | `/ws/chat/<conversation_id>/?token=...` | WS | Authenticated + signed ws token + participant validation | ❌ | Frontend Chat page currently uses polling; no websocket integration. |

### Buyer/seller chat rules verification
- Buyer initiates chat only with seller: enforced via `get_or_create` (`buyer=request.user`, `seller=product.seller`, and self-chat blocked).
- Seller replies only inside participant conversation: enforced by `conversation.user_is_participant` check in message create path.
- Seller-to-seller arbitrary messaging: indirectly prevented because conversation creation is product-mediated with buyer=request.user and self-conversation blocked.

### Critical integration mismatch
- React `getChatMessages` calls `/chat/messages/?conversation=<id>`, but `MessageViewSet` list is not explicitly filtered by that query parameter in view logic; this can return all messages across user’s conversations and leak/mix message streams in UI.

---

## 4) Assistant/AI module

| Module | Endpoint | Method(s) | Permissions/Auth | React coverage | Notes |
|---|---|---|---|---|---|
| assistant | `/assistant/api/chat/` | POST | Public (`AllowAny`) + anon/user throttle | ✅ | Used by floating `AssistantChat`. |
| assistant | `/assistant/api/chat/session/<session_id>/` | GET | Public (`AllowAny`) | ❌ | No frontend usage found. |
| assistant | `/assistant/api/chat/session/<session_id>/reset/` | POST | Public (`AllowAny`) | ❌ | No frontend usage found. |
| assistant | `/assistant/api/chat/sessions/` | GET | Manual auth check in view | ❌ | No assistant inbox page/wiring found. |
| assistant | `/assistant/api/chat/health/` | GET | Public | ❌ | Monitoring only. |
| assistant | `/assistant/api/tts/` | POST | Public | ❌ | No TTS playback flow wired. |
| assistant | `/assistant/api/tts/health/` | GET | Public | ❌ | Monitoring only. |
| assistant | `/assistant/api/ask/` | POST | Public | ❌ | Legacy endpoint not used. |
| assistant | `/assistant/api/report/` | POST | Public + throttle | ❌ | Not wired from React assistant flow. |
| assistant | `/assistant/api/report/<id>/evidence/` | POST | Authenticated | ❌ | No UI wiring. |
| assistant | `/assistant/api/report/<id>/evidence/list/` | GET | Authenticated | ❌ | No UI wiring. |
| assistant | `/assistant/api/report/<id>/close/` | POST | Authenticated | ❌ | No UI wiring. |
| assistant | `/assistant/api/legacy/chat/` | POST | Public (csrf_exempt legacy path) | ❌ | Not used. |
| assistant | `/assistant/api/admin/logs/` | GET | Staff-only check in view | ❌ | No admin UI wiring found. |
| assistant | `/assistant/api/admin/reports/` | GET | Staff-only check in view | ❌ | No admin UI wiring found. |
| assistant | `/assistant/api/docs/` | GET | Public | ❌ | Docs endpoint. |
| assistant | `/assistant/api/about/` | GET | Public | ❌ | Info endpoint. |

### Assistant session behavior verification
- Logged-out users are handled as ephemeral (no DB writes) with short-lived cookie session (`assistant_temp_session`) and metadata marked temporary. ✅
- Logged-in path uses `ConversationManager`, which creates or updates persistent `ConversationSession` rows. ✅
- Existing sessions are not overwritten by default: manager does `get_or_create` by `session_id`; updates are constrained and title generation is one-time. ✅
- Gap: there is no explicit “migrate ephemeral to inbox” contract endpoint. Current behavior is branch-by-auth-state, not user-controlled migration from temporary to persistent thread.

---

## Step 2 — React integration checks (parameters/contracts)

### Confirmed good contracts
- Accounts login/register/verify/resend payload fields align with backend expectations.
- Google auth button posts `{ token }` to `/api/accounts/auth/google/`, which matches backend serializer contract.
- Assistant chat posts `{ message, session_id?, user_id? }`, matching chat endpoint contract.

### Parameter/contract mismatches and risks
1. **Home featured products query mismatch**
   - Frontend calls `getProducts({ featured: true })`, but backend `ProductListCreateView.get_queryset()` does not apply a `featured` filter parameter.
   - Result: homepage “featured” section may show non-featured items.

2. **Marketplace chat message list mismatch**
   - Frontend uses `/chat/messages/?conversation=<id>`.
   - Backend does not implement explicit `conversation` query filtering in `MessageViewSet` list.
   - Result: possible overfetch/mixed messages and poor scalability.

3. **JWT refresh not integrated into retry flow**
   - Refresh endpoint exists in API module but no robust interceptor or context strategy on 401.
   - Result: abrupt logouts under token expiry at scale.

4. **Product field naming drift in UI components**
   - Backend serializers expose `title`, while some frontend components use `product.name` fallbacks.
   - Result: subtle rendering blanks/inconsistencies.

---

## Step 3 — Product sharing & security report

## Current status
- Unique product slug/ID: implemented and enforced.
- Share authorization rules requested in objective: **not implemented** (no share endpoint or policy layer).
- `shares_count` metric exists but no controlled API path to mutate it safely.

## Recommendation
- Add `POST /api/market/products/<slug>/share/` with policy checks:
  - buyer share allowed only if recorded view/purchase context exists,
  - seller share allowed only if owner of product,
  - reject others with 403,
  - create immutable `ProductShareEvent` records for audits and anti-fraud analytics.

---

## Step 4 — Chat & AI separation verification

## Separation status
- Assistant module is HTTP/DRF endpoints (no assistant websocket routing/consumer). ✅
- Marketplace chat has REST + dedicated WebSocket consumer/routing. ✅
- No direct backend cross-contamination found in routing.

## Integration gap
- Frontend `Chat` page is still polling REST and does not consume websocket transport/token returned by `get_or_create` action.
- This weakens real-time UX and increases DB/API load under concurrency.

---

## Step 5 — AI session & inbox behavior

## What is working
- Ephemeral logged-out assistant path with temporary session cookie and no persistence.
- Persistent logged-in assistant sessions via `ConversationSession` with unique `session_id`.
- Session reuse respects ownership checks (`PermissionError` if authenticated user doesn’t own existing session).

## Gaps
- No explicit endpoint to migrate anonymous/ephemeral thread into authenticated inbox while preserving history.
- No frontend inbox list/detail UI for assistant sessions, despite backend `list_sessions` support.
- `session_status` and `reset_session` are `AllowAny`; exposure may be broader than intended for a multi-tenant inbox model.

---

## Step 6 — Frontend/React design readiness review

## Homepage
- Strengths:
  - Clear hero, CTA structure, feature cards, and product grid are present.
  - Dark/light theming support exists.
- Gaps:
  - Hero visual uses SVG/gradient placeholder block rather than branded imagery.
  - No brand logo asset (navbar uses text “ZUNTO” only).
  - No real placeholder image file found for product fallback (`/placeholder.png` missing).
  - “Featured” semantics are visually present but data source may not be truly featured-filtered.

## Product views
- Strengths:
  - Product details layout is substantial (gallery, price, ratings, stock, reviews hooks).
- Gaps:
  - Fallback references `/placeholder.png`, but asset missing.
  - Field mapping inconsistencies (`name` vs backend `title`) can degrade display quality.

## Dashboard / Inbox readiness
- Dashboard pages exist, but assistant inbox/session management UI is not present.
- Marketplace inbox (`/chat`) exists but lacks websocket integration and advanced conversation actions (transaction confirms, read receipts UI, typing indicators).

## Chat widget integration
- Floating assistant widget is integrated globally and functionally connected.
- Missing production-grade controls:
  - no explicit user control to convert temporary guest chat to persistent inbox thread,
  - no assistant lane switch UX (inbox vs customer_service),
  - no threaded history panel beyond in-widget state.

## Recommended AI-generated placeholder assets
- Homepage hero image: “premium e-commerce marketplace scene, modern African tech aesthetic, blue-purple neon accents, clean studio lighting”.
- Category banners: minimal product collages per category with brand-consistent gradient overlay.
- Product fallback image set: neutral product silhouettes (electronics/fashion/home).
- Brand system pack: logo mark, wordmark, favicon, and monochrome variants.

---

## Step 7 — Structured recommendations by module

## Accounts
1. Wire missing frontend flows: password reset, email verify/resend, change password.
2. Add centralized token-refresh + retry interceptor.
3. Add explicit session invalidation UX and refresh-token rotation handling.

## Products/Market
1. Align featured product query contract (either backend filter support or frontend use `/featured/`).
2. Implement share endpoint and role-based share policy checks.
3. Add seller media management UI (upload/delete image/video) and product lifecycle actions (mark sold/reactivate).
4. Normalize field names (`title` vs `name`) across serializers and frontend models.

## Chat (Marketplace)
1. Use `conversations/<id>/messages/` for scoped retrieval or add safe `conversation` filter in `MessageViewSet.list`.
2. Integrate websocket client using ws token from `get_or_create` for real-time updates.
3. Add UI support for confirm sale/receipt and transaction status.
4. Add pagination/infinite scroll for large conversations (avoid full polling every 3s).

## Assistant (AI)
1. Add explicit migration API from ephemeral guest thread to authenticated persistent inbox thread.
2. Build assistant inbox UI consuming `list_sessions`, `session_status`, and reset controls with authorization hardening.
3. Consider tightening access for session detail/reset to authenticated owner-only for inbox lane.
4. Expose lane selection in frontend and isolate dispute/customer-service experience clearly.

---

## Step 8 — Scalability & concurrency risks (10k+ users)

1. Polling chat every 3 seconds per active user will over-stress DB/API; websocket should be primary transport.
2. Message list overfetch risk (`/chat/messages/` unscoped list usage) can inflate payloads and lock contention.
3. Token refresh gap will increase auth failures and repeated login churn under long sessions.
4. Assistant endpoints with `AllowAny` on session introspection/reset may become abuse vectors without stricter ownership checks and throttling envelopes.
5. Missing share-policy endpoint means business rules are unenforceable and analytics (`shares_count`) can become inconsistent.

---

## Executive summary
- Backend foundations are solid and modularly separated (assistant vs marketplace chat).
- Major gaps are mostly integration/contract/UI completeness, not core endpoint absence.
- Priority order for near-term production hardening:
  1) fix chat retrieval contract + websocket integration,
  2) complete auth lifecycle UX + token refresh strategy,
  3) implement product sharing policy endpoint,
  4) deliver assistant inbox migration and session ownership hardening,
  5) finalize branding/imagery placeholders for premium visual readiness.

---

## Incremental delivery plan (phase-wise)

The remediation should be delivered in three deployable phases so that production stability improvements can ship first without waiting for wider product scope.

### Phase 1 — Production stability & correctness (ship first)

**Goal:** Remove the highest-risk correctness and scale issues in current live traffic paths.

**Backend endpoints/modules in scope**
- **Chat:**
  - Fix message scoping contract for `GET /chat/messages/` **or** standardize frontend on `GET /chat/conversations/<id>/messages/`.
  - Keep participant-only access enforcement intact.
- **Chat WebSocket path:** `/ws/chat/<conversation_id>/?token=...` (existing) to be actively consumed by frontend.
- **Accounts auth resilience:**
  - Use existing `POST /api/accounts/token/refresh/` for automatic refresh/retry behavior.

**Frontend integrations in scope**
- Update `Chat` page data flow to avoid mixed-conversation overfetch and wire real-time updates using ws token from `POST /chat/conversations/get_or_create/`.
- Add centralized API refresh flow (interceptor/wrapper): on 401, refresh token once, retry request, otherwise logout.
- Standardize product field mapping where critical to avoid blank labels in high-traffic views (`title` vs `name` mismatch hotspots).

**Deployability/acceptance criteria**
- Conversation view only renders messages for the selected conversation.
- New incoming messages appear in real time (no 3s polling dependency for primary path).
- Expired access tokens refresh transparently for active users.

---

### Phase 2 — Business rules + missing UX wiring

**Goal:** Implement explicit marketplace policy rules and close key user journey gaps.

**Backend endpoints/modules in scope**
- **Products/Market:**
  - Add explicit product sharing endpoint (e.g., `POST /api/market/products/<slug>/share/`) with policy enforcement:
    - buyer can share viewed/owned-context products,
    - seller can share only own products,
    - others forbidden.
  - Add share event/audit model for traceability and accurate `shares_count` updates.
- **Accounts:** complete lifecycle endpoint usage already available:
  - `POST /api/accounts/change-password/`
  - `POST /api/accounts/verify-email/`
  - `POST /api/accounts/resend-verification/`
  - `POST /api/accounts/password-reset/request/`
  - `POST /api/accounts/password-reset/confirm/`
- **Products media/lifecycle wiring (existing endpoints):**
  - images/videos upload/delete
  - mark sold/reactivate
  - stats/similar/favorites/report UX surfacing.

**Frontend integrations in scope**
- Add UX for password reset + email verification + change password.
- Add seller product lifecycle controls and media management screens.
- Add share action in product views tied to new policy endpoint.

**Deployability/acceptance criteria**
- Share attempts obey role/ownership/view rules with deterministic 403/200 behavior.
- Auth lifecycle flows are fully operable from SPA without manual API calls.
- Seller product operations are executable from dashboard/product management UI.

---

### Phase 3 — Assistant inbox, migration, and design polish

**Goal:** Improve assistant experience and visual readiness after core/platform stabilization.

**Backend endpoints/modules in scope**
- **Assistant:**
  - Add explicit ephemeral→persistent migration contract (new endpoint) for logged-in opt-in inbox save.
  - Harden session ownership for session detail/reset paths (owner-auth model for inbox lane).
  - Expand assistant inbox APIs only as needed for thread list/detail/rename/reset UX.

**Frontend integrations in scope**
- Build assistant inbox UI using:
  - `GET /assistant/api/chat/sessions/`
  - `GET /assistant/api/chat/session/<session_id>/`
  - `POST /assistant/api/chat/session/<session_id>/reset/`
  - migration endpoint from ephemeral widget thread.
- Add lane-selection UX (inbox vs customer_service) and clearer dispute handoff.
- Visual polish:
  - real placeholder assets,
  - brand logo/wordmark/favicon,
  - improved homepage hero/product fallback imagery.

**Deployability/acceptance criteria**
- Guest assistant sessions remain temporary unless explicitly migrated.
- Logged-in users can browse persistent assistant threads in inbox UI.
- Core branding/assets are present and no broken placeholder references remain.

---

## Recommended execution sequence and release cadence

1. **Release A (Phase 1):** chat correctness + websocket + token refresh reliability.
2. **Release B (Phase 2):** business-rule enforcement and missing critical user flows.
3. **Release C (Phase 3):** assistant inbox/migration and design/brand polish.

This sequencing minimizes risk by first resolving correctness/scalability concerns, then enforcing policy/business completeness, then delivering higher-level UX enhancements.
