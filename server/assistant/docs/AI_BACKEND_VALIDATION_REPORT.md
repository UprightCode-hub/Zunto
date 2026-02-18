# AI Backend Validation Report (Phase 1 + React Integration Readiness)

## Scope reviewed
- AI module orchestration and flows
- Chat module (WebSocket + REST)
- Account/auth + OAuth interactions relevant to AI/chat
- Settings and URL integration paths required for React

## Executive status
- **Current status: NOT production-ready** for AI assistant + chat integration as-is.
- The codebase has strong building blocks, but there are several critical integration mismatches and runtime risks.

---

## 1) AI orchestration refactor checks

### 1.1 Unified confidence in `constants.py`
**Status:** Partially complete.

- `ConfidenceConfig` is centralized and used by `QueryProcessor` for RAG decisioning.
- However, `FAQFlow` still uses hardcoded tiers (`0.65`, `0.40`) instead of consuming `ConfidenceConfig`.

**Risk:** confidence behavior can drift between modules.

### 1.2 ContextManager integrated into QueryProcessor
**Status:** Partially complete.

- `ConversationManager` passes `session.context` into `QueryProcessor.process(...)` when flag enabled.
- `QueryProcessor` consumes context for score boost and LLM prompt enrichment.

**Gap:** context usage is indirect (via `ConversationManager`) rather than explicit `ContextManager` dependency in `QueryProcessor`.

### 1.3 Intent classification cached and not duplicated
**Status:** Not complete.

- Message-level cache exists in `ConversationManager._message_intent_cache`.
- But duplicate classification still happens in `FeedbackFlow._detect_sentiment()` when `intent_classifier=True`, causing a second call to `classify_intent(...)` for same message.

**Risk:** unnecessary overhead and possible intent metadata inconsistency per turn.

### 1.4 State machine centralized
**Status:** Partially complete.

- Central routing is in `ConversationManager.process_message(...)` by state.
- But some state strings in flows are hardcoded (`'faq_mode'`, `'menu'`, etc.) instead of shared constants.

**Risk:** typo regressions and fragile refactors.

### 1.5 RAG/LLM fallback logic
**Status:** Design exists but has critical runtime bug.

- Intended pipeline: Rules -> RAG -> LLM.
- `LocalModelAdapter.generate(...)` returns a dict payload.
- `QueryProcessor._query_llm(...)` treats it as a plain string (`len(response.split())`, confidence estimator expecting `str`).

**Risk:** LLM stage can error or silently degrade whenever fallback executes.

---

## 2) AI session handling checks

### 2.1 New session on hover
**Status:** Cannot confirm as implemented.

- No explicit backend endpoint dedicated to "init session on hover".
- Session is created lazily in `chat_endpoint` only when request omits `session_id`.

**Conclusion:** Hover-based pre-session behavior is not currently guaranteed by backend contract.

### 2.2 Preserve stored history and avoid overwriting old sessions
**Status:** Mostly correct backend behavior.

- New UUID session IDs create new `ConversationSession` records.
- Existing IDs reuse existing sessions.

**Frontend caveat:** current widget persists one `chat_session_id` in localStorage and reuses it indefinitely; this does not represent "new session per hover" UX.

---

## 3) AI and Chat separation checks

### 3.1 AI module uses WebSocket?
**Status:** Separated correctly.

- AI assistant endpoint is HTTP/DRF view-based.
- WebSockets are confined to `chat` app consumer/routing.

### 3.2 Buyer/seller restrictions in chat
**Status:** Participant access control is present; role-policy is not explicit.

- Conversation membership checks enforce only buyer/seller participants can access/send.
- Conversation creation enforces buyer=user and seller=product.seller.

**Gap:** no explicit role-level policy (e.g., "buyers can initiate only", "sellers reply only") beyond participant model.

### 3.3 Cross-contamination AI vs chat
**Status:** Mostly separated in backend.

**Major frontend integration issue:** shared `sendChatMessage(...)` API helper currently points to `/chat/send/` and is used by both marketplace chat page and assistant widget.

**Impact:** assistant UI is not wired to assistant backend endpoint.

---

## 4) Database usage and dispute readiness

### 4.1 AI read access to buyer/seller data for disputes
**Status:** Limited.

- Dispute flow currently stores user-provided description/category and creates `Report`.
- No structured fetch of order/seller/buyer transactional entities in dispute flow.

### 4.2 Dispute information capture quality
**Status:** Acceptable baseline, not full-resolution grade.

- Prompts user for what happened, when, who involved, order details.
- Good starter UX, but no enforced required fields/validation schema before report create.

### 4.3 Multiple conversations for different products
**Status:** Correct for marketplace chat.

- `Conversation` uniqueness is `(buyer, seller, product)` which cleanly separates product threads.

---

## 5) React API integration readiness

### 5.1 AI endpoint reachability
**Status:** Broken by router configuration.

- `assistant/urls.py` defines `/assistant/api/chat/...` endpoints.
- Main project URLConf has assistant include commented out, so endpoints are not exposed.

### 5.2 Session ID compatibility with frontend
**Status:** Partially ready backend; frontend mismatch.

- Backend supports optional `session_id`, returns `session_id` consistently.
- Frontend assistant widget currently calls wrong endpoint helper and therefore cannot reliably leverage this contract.

### 5.3 OAuth compatibility
**Status:** Mostly good, one config dependency.

- Frontend posts Google credential to `/api/accounts/auth/google/`.
- Backend verifies token using `settings.GOOGLE_OAUTH_CLIENT_ID`.

**Required config:** ensure `GOOGLE_OAUTH_CLIENT_ID` is present in environment for all deployed environments.

---

## 6) Backward compatibility checks

### 6.1 Login/logout/google auth impact
**Status:** No direct break found from AI/chat modules.

### 6.2 Existing chat functionality impact
**Status:** Backend robust, but frontend wiring currently not aligned with new chat API conventions.

---

## Critical issues (fix before deployment)

1. **Assistant routes not mounted** in project URLConf.
2. **LLM return-type mismatch** between `LocalModelAdapter` and `QueryProcessor`.
3. **Frontend assistant and marketplace chat share wrong helper endpoint** (`/chat/send/`) that does not map to assistant API contract.
4. **Duplicate intent classification** in feedback path.

## High-priority warnings

1. `GreetingFlow.start_conversation()` calls `ContextManager.add_message(..., metadata=...)` but `ContextManager.add_message` has no `metadata` parameter.
2. `FAQFlow` reads `result.get('faq')` while processor populates `faq_hit`; metadata linkage likely lost.
3. `FAQFlow.get_popular_faqs()` references `self.query_processor.rag` but processor attribute is `rag_retriever`.
4. `chat_endpoint` is CSRF-exempt even though middleware comment indicates only health/docs endpoints should bypass CSRF checks.

---

## Recommended correction plan (no code here)

1. **Restore assistant URL mounting** in main URLConf; verify endpoint with curl/postman.
2. **Normalize LLM adapter contract** (choose string or dict), then update all call sites consistently.
3. **Split frontend API helpers**:
   - Assistant helper -> `/assistant/api/chat/`
   - Marketplace chat helpers -> `/chat/...` REST + WS token flow
4. **Eliminate duplicate classification** by passing already-classified metadata into feedback flow.
5. **Replace hardcoded thresholds/states** in flows with constants from `assistant/utils/constants.py`.
6. **Fix flow-level integration mismatches** (`faq_hit` key, `rag_retriever` attribute, `add_message` signature usage).
7. **Define explicit role policy** for buyer/seller initiation/reply if product requires stricter behavior.
8. **Session UX contract**:
   - Add explicit session-init endpoint (or documented no-message init behavior)
   - Implement hover-triggered session bootstrap in React if that UX is required.
9. **Security hardening**: re-evaluate broad CSRF exemptions and ensure OAuth client ID configuration checks are surfaced at startup.

---

## Missing files / inputs requested for complete verification

To fully validate "hover starts new AI session" and production integration, these are needed:

1. React component(s) responsible for the AI floating button hover event (if different from `AssistantChat.jsx`).
2. Any frontend service wrapper dedicated to assistant endpoints (if exists outside `client/src/services/api.js`).
3. Deployment env samples for backend containing OAuth/assistant variables (`GOOGLE_OAUTH_CLIENT_ID`, `GROQ_API_KEY`, Redis/channel settings).
4. Any Nginx/proxy config that rewrites `/assistant/*` or `/chat/*` paths.

