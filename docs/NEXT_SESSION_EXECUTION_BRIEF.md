# Next Session Execution Brief (Single Source)

_Last updated: 2026-02-22 (UTC)_

## Purpose
Concise, execution-first handoff for backend + frontend parity work. This file replaces scattered notes and should be treated as the primary next-session reference.

## Current Platform Status (Essential Only)
- **Phase 1:** complete.
- **Phase 2:** complete.
- **Phase 3:** partial — async malware lifecycle not complete across all upload domains.
- **Phase 4:** partial — admin/company operations parity advanced, but cross-domain admin audit coverage still incomplete.
- **Phase 5:** partial — diagnostics/runbook exist, full alert automation and dashboard maturity still pending.
- **Phase 6:** partial — object storage baseline exists, direct upload lifecycle still incomplete.

## Company Admin Portal Integration (What Exists)
- Backend + frontend parity already shipped for:
  - Product report moderation queue/actions.
  - Review flag moderation queue/actions.
  - Bulk refund approve/reject action.
  - Company ops summary endpoint and ops tab queue filters/pagination.
- Current admin mutation audit events include:
  - `orders.item.status_updated` (domain-level)
  - `orders.admin.order_item_status_updated` (admin actor specific)
  - `assistant.report.closed` (domain-level close)
  - `assistant.admin.report.closed` (staff/admin close path)
  - `reviews.flag.moderated` (domain-level moderation)
  - `reviews.admin.flag.moderated` (admin moderation path)
  - `assistant.report.evidence_validation_enqueue_failed` (fail-closed when async validation queue is unavailable)
  - `notifications.admin.email_templates.viewed` (admin template listing)
  - `notifications.admin.email_statistics.viewed` (admin email metrics listing)

## High-Priority Pending Work (Execution Order)
1. **Phase 4 (continue now):**
   - Expand `audit_event` coverage for remaining high-impact admin mutations (orders/reviews/notifications/assistant/admin-only write actions).
   - Add/extend backend tests for each added admin mutation event.
   - Verify frontend audit consumers do not miss new event names.
2. **Phase 3:**
   - Complete async malware status lifecycle (`pending/clean/quarantined/rejected`) for all relevant upload flows.
3. **Phase 5:**
   - Wire automated alert routing from `/health/` diagnostics thresholds (queue depth/worker degradation).
4. **Phase 6:**
   - Finish signed direct-upload + callback verification + quarantine/promotion object flow.

## Backend ↔ Frontend Contract Notes (Keep in Sync)
- `PATCH /api/orders/seller/items/<item_id>/update-status/`
  - Contract unchanged.
  - Audit stream now may include both `orders.item.status_updated` and `orders.admin.order_item_status_updated`.
- Admin operations queue/actions remain centered on:
  - Product reports moderation endpoints.
  - Review flags moderation endpoints.
  - Bulk refund decision endpoint.

## Definition of Done for the Next Chunk
- One additional pending Phase 4 admin mutation path audited.
- Matching tests added/updated.
- If frontend impact exists, update service-layer/handoff notes in this file only.
- Commit + PR notes recorded.

## Startup Checklist
1. Read this file.
2. Confirm latest commit on `work`.
3. Pick one pending item only.
4. Implement + run available tests/checks.
5. Update only this brief (avoid creating parallel long-form handoff docs).
