# Phase 3 Plan Artifact — Sub-phase 3.1 (WebSocket Event Protocol Contract)

Aligned to `docs/inbox-ai-restructure-architecture.md` as the authoritative source.  
Scope here is planning only for `/inbox` WebSocket marketplace chat domain.

## 0) Guardrails (must remain true throughout Phase 3)

- `/inbox` remains WebSocket marketplace chat only.
- `/inbox/ai` remains REST-only assistant workspace (no WS protocol sharing).
- `/chat` remains customer_service-only isolated flow.
- No assistant entities, lane logic, or transport logic may enter `/inbox` WS modules.
- No WebSocket event machinery may be introduced into `/inbox/ai`.
- No transport merging, no cross-domain shared reducer/store for chat+assistant.

## 1) Sub-phase 3.1 Objective

Define and lock a versioned WebSocket event protocol contract for marketplace chat in `/inbox`, including validation, normalization, strict routing, and safety behavior for malformed/unknown payloads.

**Outcome:** protocol spec + server/client enforcement design + “ready to implement” acceptance checklist.

## 2) Event Protocol Contract Design

### 2.1 Canonical event envelope (all WS events)

Use one envelope for every inbound/outbound WS message:

- `v` (`string`): protocol version (e.g. `"1.0"`).
- `type` (`string`): event type name (namespaced).
- `event_id` (`string`): globally unique event identifier (UUID/ULID).
- `conversation_id` (`string`): chat thread identifier.
- `actor_id` (`string|null`): sender/user that emitted the event.
- `occurred_at` (`ISO8601 string`): server-authoritative timestamp where possible.
- `seq` (`number|null`): monotonic per-conversation sequence assigned by server.
- `correlation_id` (`string|null`): links ack/error to originating client action.
- `idempotency_key` (`string|null`): for dedupe of client-originating commands.
- `payload` (`object`): type-specific body.
- `meta` (`object`, optional): non-domain diagnostics (trace id, shard, etc).

**Rules**

- Envelope keys are fixed and validated before type-specific parsing.
- Unknown top-level keys tolerated but ignored (forward compatibility).
- `type`, `v`, `event_id`, `conversation_id`, `payload` are required for domain events.

### 2.2 Event naming + versioning strategy

- Namespaced types: `chat.message.created`, `chat.typing.started`, etc.

Separate semantic axes:

- `v` = envelope/protocol version.
- `type` = behavior contract.

**Version policy**

- Additive payload fields: same `v`.
- Breaking schema/type semantics: bump `v` (e.g. `1.x -> 2.0`) and support dual-read window.

**Deprecation policy**

- Server can emit both legacy and canonical shapes during migration window.
- Client parser normalizes legacy to canonical internal model.
- Sunset date/version gates defined before removing legacy support.

### 2.3 Required event types (minimum for 3.1 contract)

**Message lifecycle**

- `chat.message.send` (client->server command)
- `chat.message.ack` (server->client acceptance/rejection of command)
- `chat.message.created` (server broadcast definitive persisted message)
- `chat.message.updated` (edit/system enrichment; optional if supported)
- `chat.message.deleted` (if delete semantics exist)
- `chat.history.synced` (snapshot/replay window on reconnect)

**Typing**

- `chat.typing.started`
- `chat.typing.stopped`

**Presence**

- `chat.presence.online`
- `chat.presence.offline`
- `chat.presence.snapshot` (initial roster/state)

**Read receipts**

- `chat.read.updated` (actor read watermark advanced)
- `chat.read.snapshot` (on thread open/reconnect)

**Errors & control**

- `chat.error` (structured domain/protocol error)
- `chat.warning` (non-fatal contract downgrade info)
- `chat.ping` / `chat.pong` (keepalive, latency)
- `chat.replay.request` / `chat.replay.chunk` / `chat.replay.complete` (if replay is explicit)

### 2.4 Backward compatibility for legacy payloads

Introduce a normalization layer before business handlers:

- Detect legacy signatures (missing `v`, alternate field names, old event key, etc).
- Map legacy fields -> canonical envelope.
- Annotate normalization origin in `meta.normalized_from`.

**Strict fallback**

- If cannot normalize safely, route to `chat.error` handling path and drop from domain reducers.

**Compatibility window**

- Define N-release overlap where server accepts old command shape and emits canonical responses.
- Instrument metrics for legacy usage; remove only after near-zero traffic.

## 3) Validation and Enforcement Strategy

### 3.1 Server-side validation/normalization

**Inbound (client->server)**

- Parse JSON safely.
- Envelope schema validation (required keys, types, max sizes).
- Type-level schema validation (payload shape by type).
- Authz checks (`actor_id` ownership, conversation membership).
- Idempotency check (`idempotency_key` + actor + conversation scope).
- Normalize to canonical internal event object.
- Persist/broadcast with server-assigned `seq` and authoritative timestamp.

**Outbound (server->client)**

- Emit only canonical envelope for new clients.
- Optional legacy mirror stream during migration flag period.
- Guarantee per-conversation ordering by `seq` in emitted stream.

### 3.2 Client-side parsing and strict handler routing

**Pipeline**

- Parse JSON.
- Envelope validator.
- Version gate (`v` supported?).
- Event type dispatcher table (exact-match handlers only).
- Per-type payload validation before reducer mutation.
- Unknown/malformed events: quarantine/log path, no state mutation.

**Rules**

- No “catch-all mutate” handler.
- Reducers only accept normalized typed action DTOs.
- Any parsing failure is non-fatal to socket lifecycle unless threshold exceeded.

### 3.3 Malformed/unknown event safety

- Malformed JSON: drop + telemetry counter.
- Unknown `type`: ignore + telemetry + optional `chat.warning`.
- Unsupported `v`: emit compatibility warning and optional reconnect fallback.
- Missing critical IDs (`conversation_id`, `event_id`): drop hard.
- Rate-limit error logging to avoid storm loops.

## 4) State Management Impact (`/inbox` WS domain only)

### 4.1 Mapping protocol to `/inbox` state transitions

- `chat.message.created` -> append/merge message entity, update last message preview/time.
- `chat.history.synced` -> hydrate thread window + pagination cursors.
- `chat.typing.*` -> ephemeral typing map keyed by conversation+actor with TTL.
- `chat.presence.*` -> participant presence map with heartbeat expiry.
- `chat.read.*` -> per-conversation read watermark by actor.
- `chat.error` -> non-blocking UI/system banner state; no domain corruption.

### 4.2 Ordering + idempotency

- Primary ordering key: server `seq` per conversation.
- Secondary tie-breaker: `occurred_at`, then `event_id`.
- Buffer out-of-order events briefly (small reorder window), then apply deterministically.
- Idempotent reducer behavior keyed by `event_id` (processed-event cache with TTL).
- Command dedupe via `idempotency_key` on send path.

### 4.3 Duplicate event handling

- If `event_id` already processed: no-op (except metrics).
- If same message ID with newer revision/version: merge update.
- If duplicate with conflicting payload: keep highest `seq`, flag anomaly metric.

## 5) Risk Analysis (3.1-focused)

### 5.1 Race conditions

- Send-vs-ack-vs-broadcast race (optimistic UI vs definitive event).
- Concurrent read receipt updates from multiple devices.
- Typing stop lost on disconnect (stale typing state).

**Mitigation**

- Optimistic entries reconcile on `chat.message.created` via `correlation_id`.
- Read watermarks monotonic max.
- Typing TTL auto-expiry + disconnect cleanup.

### 5.2 Ordering and clock drift

- Client clocks are non-authoritative.
- Server assigns `seq` and canonical time.
- UI rendering uses sequence order; display time can still show server timestamp.

### 5.3 Reconnect/replay edge cases

- Gap detection using last seen `seq`.
- On reconnect: request replay from `last_seq + 1` or receive `history.synced`.
- If replay window unavailable, force bounded snapshot resync.
- Ensure replay is idempotent against local cache.

### 5.4 Throughput/performance at scale

- Minimize payload size (compact envelope keys if needed, but keep clarity first).
- Batch replay chunks for large gaps.
- Enforce max event size and rate limits per connection.
- Keep ephemeral domains (typing/presence) out of heavy persistent reducers.
- Instrument parser latency, dropped-event counts, reorder-buffer pressure.

## 6) Immediate Follow-on Sequencing (after 3.1)

### 3.2 Typing indicators

- Implement `typing.started`/`typing.stopped` with debounce/throttle rules.
- TTL cleanup and disconnect expiration.
- UI integration strictly in `/inbox` WS store.

### 3.3 Presence

- Presence snapshot + incremental online/offline events.
- Heartbeat policy and staleness expiration.
- Conversation list presence badges.

### 3.4 Read receipts

- Watermark model per actor/conversation.
- Server monotonic enforcement.
- Thread + list unread reconciliation.

### 3.5 Reliability/performance hardening

- Replay robustness, backpressure controls, message size/rate guards.
- Metrics dashboards + alert thresholds for protocol failures.
- Load-focused tuning for 10k concurrent target constraints.

### 3.6 Isolation/regression guardrails

- Lint/static boundaries to prevent `/inbox` WS importing assistant modules.
- Test gates for no `/inbox/ai` WS usage and no `customer_service` leakage.
- Contract tests to ensure event schemas remain version-safe.

## 7) Sub-phase 3.1 Acceptance Criteria (“Ready to Implement” Checklist)

- [ ] Canonical WS envelope fields finalized and documented in engineering spec.
- [ ] Event type catalog defined for message lifecycle, typing, presence, read, errors.
- [ ] Versioning + deprecation policy approved (including legacy window).
- [ ] Server validation + normalization flow specified (schema + authz + idempotency).
- [ ] Client strict parser/dispatcher contract specified (no catch-all mutation path).
- [ ] Unknown/malformed event handling behavior defined and safe.
- [ ] Ordering/dedupe/idempotency rules agreed (`seq`, `event_id`, `idempotency_key`).
- [ ] Reconnect/replay strategy defined with gap detection behavior.
- [ ] Telemetry metrics list finalized (drops, unknown types, reorder, parse errors, duplicates).
- [ ] Explicit domain isolation checks included:
  - no assistant logic in `/inbox` WS,
  - no WS logic in `/inbox/ai`,
  - no `/chat` `customer_service` boundary violations.

## Suggested implementation start order once planning is approved

1. Contract schema definitions + shared validator interfaces.
2. Server ingress validation + canonical emission.
3. Client parser/normalizer + strict dispatcher.
4. Reducer idempotency/order buffer integration.
5. Replay/gap handling and telemetry hooks.
6. Then execute 3.2 -> 3.6 in sequence above.


## 8) Alignment Confirmation Against Authoritative Architecture

This artifact is constrained to and consistent with `docs/inbox-ai-restructure-architecture.md`:

- `/inbox` scope remains marketplace chat WebSocket protocol planning only (chat domain).
- `/inbox/ai` remains REST-only assistant workspace and is intentionally excluded from this protocol contract.
- `/chat` remains customer-service isolated and excluded from this event protocol.
- No cross-domain shared reducer/store or transport unification is introduced by this plan.
- This artifact defines contract and enforcement design only; it does not redefine backend lane contracts, route policy, or assistant model semantics.

Implementation-readiness for 3.1 is satisfied by: canonical envelope lock, event catalog lock, validation/normalization pipeline definition, strict client dispatcher behavior, deterministic ordering/idempotency rules, replay/gap strategy, telemetry requirements, and explicit acceptance checklist above.
