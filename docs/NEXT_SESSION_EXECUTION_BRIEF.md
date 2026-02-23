# Next Session Execution Brief (Single Source)

_Last updated: 2026-02-22 (UTC)_

## Purpose
Concise, execution-first handoff for backend + frontend parity work. This file replaces scattered notes and should be treated as the primary next-session reference.

## Current Platform Status (Essential Only)
- **Phase 1:** complete.
- **Phase 2:** complete.
- **Phase 3:** partial — async malware lifecycle still incomplete across all upload domains; product-video fail-open retry path now preserves `pending` state without a false completion timestamp.
- **Phase 4:** partial — admin/company operations parity advanced; moderation queue reads plus product media/status/direct-upload/product-create, seller-statistics, and assistant report/evidence and market report-create admin parity now include paired domain/admin events, with only a small set of cross-domain admin mutation/read audit gaps remaining.
- **Phase 5:** partial — diagnostics/runbook exist; backend email alert routing with cooldown is wired; baseline webhook alert routing is now added with non-fatal delivery failure handling, while broader dashboard/incident automation maturity is still pending.
- **Phase 6:** partial — object storage baseline exists; direct-upload callback now has replay/key-scope validation hardening plus callback idempotency/content-type validation, but full quarantine/promotion lifecycle remains incomplete.

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
  - `assistant.report.created` / `assistant.admin.report.created`
  - `assistant.report.evidence_uploaded` / `assistant.admin.report.evidence_uploaded`
  - `assistant.report.evidence_validation_enqueue_failed` / `assistant.admin.report.evidence_validation_enqueue_failed`
  - `notifications.admin.email_templates.viewed` (admin template listing)
  - `notifications.admin.email_statistics.viewed` (admin email metrics listing)
  - `market.admin.report.moderated` (admin actor product-report moderation path)
  - `market.report.created` / `market.admin.report.created`
  - `market.admin.video_scan.moderated` (admin actor video-scan moderation path)
  - `market.product.created` / `market.admin.product.created`
  - `market.product.mark_sold` / `market.admin.product.mark_sold`
  - `market.product.reactivated` / `market.admin.product.reactivated`
  - `market.product.image_uploaded` / `market.admin.product.image_uploaded`
  - `market.product.image_deleted` / `market.admin.product.image_deleted`
  - `market.video_upload.submitted` / `market.admin.video_upload.submitted`
  - `market.video_upload.ticket_issued` / `market.admin.video_upload.ticket_issued`
  - `market.video_upload.callback_verified` / `market.admin.video_upload.callback_verified`
  - `market.report.moderation_queue_viewed` / `market.admin.report.moderation_queue_viewed`
  - `market.video_scan.queue_viewed` / `market.admin.video_scan.queue_viewed`
  - `reviews.flag.moderation_queue_viewed` / `reviews.admin.flag.moderation_queue_viewed`
  - `orders.refund.process_initiated` / `orders.admin.refund.process_initiated`
  - `orders.refund.process_failed` / `orders.admin.refund.process_failed`
  - `orders.refund.process_rejected` / `orders.admin.refund.process_rejected`
  - `orders.refund.bulk_decision_applied` / `orders.admin.refund.bulk_decision_applied`
  - `orders.seller_orders_viewed` / `orders.admin.seller_orders_viewed`
  - `orders.seller_order_detail_viewed` / `orders.admin.seller_order_detail_viewed`
  - `orders.seller.statistics_viewed` / `orders.admin.seller.statistics_viewed`
  - `notifications.email_templates.viewed` / `notifications.admin.email_templates.viewed`
  - `notifications.email_statistics.viewed` / `notifications.admin.email_statistics.viewed`
  - `assistant.logs.viewed` / `assistant.admin.logs.viewed`
  - `assistant.reports.viewed` / `assistant.admin.reports.viewed`
  - `assistant.metrics.viewed` / `assistant.admin.metrics.viewed`
  - `dashboard.overview.viewed` / `dashboard.admin.overview.viewed`
  - `dashboard.sales.viewed` / `dashboard.admin.sales.viewed`
  - `dashboard.products.viewed` / `dashboard.admin.products.viewed`
  - `dashboard.orders.viewed` / `dashboard.admin.orders.viewed`
  - `dashboard.customers.viewed` / `dashboard.admin.customers.viewed`
  - `dashboard.analytics.viewed` / `dashboard.admin.analytics.viewed`
  - `dashboard.analytics_legacy.viewed` / `dashboard.admin.analytics_legacy.viewed`
  - `dashboard.company_ops.viewed` / `dashboard.admin.company_ops.viewed`

## Most Recent Completed Chunk
- **Phase 5 increment:** automated health-alert email routing added in backend monitor task with cooldown dedupe controls and recipient configuration (`HEALTH_ALERT_NOTIFY_EMAIL_*`).
- **Phase 3 increment:** product-video async scan task lifecycle tightened so scanner-unavailable fail-open keeps item `pending` and leaves `scanned_at` unset until a real scan outcome exists; task-level lifecycle tests added.
- **Phase 6 increment:** direct-upload callback now enforces object-key product prefix and replay-token rejection to reduce object-key tampering/replay risk.
- **Phase 6 increment:** direct-upload callback now supports idempotent replay-safe return for existing object key records and validates callback content-type against allowed upload types.
- **Phase 4 increment:** orders refund admin mutation paths now emit paired domain+admin audit events with tests for process and bulk decision actions.
- **Phase 4 increment:** notifications admin read paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** assistant admin observability read paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** dashboard admin read paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** orders seller list/detail admin read paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** market/reviews moderation queue admin read paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** market product-create admin mutation path now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** market direct-upload-ticket admin mutation path now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** market direct-upload-callback admin mutation path now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** market product status admin mutation paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** market product-image admin mutation paths now emit paired domain+admin events with updated tests.
- **Phase 4 increment:** market product-video upload admin mutation path now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** orders seller-statistics admin read path now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** assistant report/evidence mutation admin parity now emits paired domain+admin events with updated tests.
- **Phase 4 increment:** market report-create admin mutation path now emits paired domain+admin events with updated tests.

## High-Priority Pending Work (Execution Order)
1. **Phase 4 (continue now):**
   - Finish the final high-impact admin mutation/read parity stragglers (cross-domain edge paths) and lock regression coverage.
   - Add/extend backend tests for each added admin mutation event.
   - Verify frontend audit consumers do not miss new event names.
2. **Phase 3:**
   - Complete async malware status lifecycle (`pending/clean/quarantined/rejected`) for all relevant upload flows.
3. **Phase 5:**
   - Run fault-drill validation for email/webhook alert routing and expand dashboard/incident orchestration maturity.
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
- One additional pending Phase 4 admin mutation path audited. ✅ (market report/video moderation admin mutation events added)
- Matching tests added/updated. ✅
- If frontend impact exists, update service-layer/handoff notes in this file only.
- Commit + PR notes recorded.

## Startup Checklist
1. Read this file.
2. Confirm latest commit on `work`.
3. Pick one pending item only.
4. Implement + run available tests/checks.
5. Update only this brief (avoid creating parallel long-form handoff docs).
