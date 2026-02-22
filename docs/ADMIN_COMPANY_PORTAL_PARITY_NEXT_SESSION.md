# Company Admin Frontend Parity Plan (Next Codex Session)

_Last updated: 2026-02-22 (UTC)_

## Goal
Provide practical parity for **company admin operations** in frontend so core issue-resolution flows do not require Django `/admin` for day-to-day operations.

## Current State (Done)
- Bulk refund decision API now available (`POST /api/payments/refunds/bulk-decision/`) with admin/staff auth + audit event (`orders.admin.refund.bulk_decision_applied`).
- Backend admin/staff guardrails exist on dashboard analytics routes.
- Review-flag moderation endpoints now exposed for frontend queue/actions (`GET/PATCH /api/reviews/reviews/flags/moderation/...`) with admin/staff auth + audit actions (`reviews.flag.moderation_queue_viewed`, `reviews.flag.moderated`).
- Frontend Admin Dashboard exists and shows:
  - analytics/sales,
  - system health,
  - company-ops queue summary (`/dashboard/company-ops/`).
- Audit events are emitted for admin dashboard read paths.

## What is still only in Django Admin (Gap)
1. **Refund bulk actions UI parity** (backend API now exists; frontend action controls and richer editing still pending).
2. **Review moderation object-level actions** (notes, status transitions, resolution metadata) beyond queue counts.
3. **Order internal-note and status-history tooling** for backoffice workflows.
4. **Advanced data-management views** (search/filter/admin inlines) across multiple domains.

## Next Session Execution Plan (single phase chunk)
### Phase 4 chunk: Company-admin action APIs + frontend controls
1. Complete frontend action wiring for existing/new backend endpoints (admin/staff-only + audited):
   - Hook refund approve/reject bulk API into Admin Dashboard operations controls.
   - ✅ Add review-flag moderation endpoint (reviewing/resolved/dismissed + notes).
   - Align product-report moderation action endpoints in frontend service layer.
2. Add frontend Admin Dashboard operations tab/components:
   - ✅ Queue cards with drill-down lists (initial implementation for product reports + review flags).
   - ✅ Action buttons for approve/reject/resolve/dismiss (initial implementation for refund bulk decision + report/flag moderation).
   - ✅ Notes editor where applicable (shared notes inputs added for refund/report/flag actions).
3. Add audit events for each mutation action and add tests.
4. ✅ Add pagination/filtering for ops lists to stay free-tier friendly (initial queue pagination controls + status/reason filters now wired in admin operations tab).

## Free-tier Constraints Guidance
- Avoid loading heavy reports by default.
- Use paginated endpoints (`page`, `page_size`) and conservative defaults.
- Cache summary counts briefly (e.g., 30–60s) where safe.
- Keep expensive cross-table aggregation off request hot paths.

## Definition of Done for parity slice
- Company admin can complete **refund** and **report/flag** moderation loops end-to-end from frontend.
- All such actions are audited (`audit_event`) with actor + object references.
- Tests cover authz (admin/staff allowed, others denied) and state transition safety.
