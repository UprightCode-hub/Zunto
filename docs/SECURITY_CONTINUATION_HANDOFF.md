# Security/Scalability Continuation Handoff (Condensed)

_Last updated: 2026-02-23 (UTC)_

This handoff was intentionally reduced to remove duplicated status text.

## Canonical file
Use `docs/NEXT_SESSION_EXECUTION_BRIEF.md` as the primary execution source.

## Security phase snapshot
- Phase 1: complete.
- Phase 2: complete.
- Phase 3: partial (async malware lifecycle completion pending).
- Phase 4: complete (cross-domain admin mutation/read audit parity implemented for covered domains).
- Phase 5: partial (alert automation/routing advanced with unhealthy + recovery notifications; broader dashboard/incident orchestration still pending).
- Phase 6: partial (direct upload lifecycle completion still pending).

## Most recent completed chunks
- Added assistant dispute evidence enqueue-failure fail-closed path:
  - marks upload `rejected` with validation reason when queue enqueue fails
  - deletes uploaded file and marks evidence deleted for safety
  - emits `assistant.report.evidence_validation_enqueue_failed` audit action.

- Added admin-specific audit event for order item status updates:
  - `orders.admin.order_item_status_updated`
  - existing domain event `orders.item.status_updated` remains.
- Added assistant report close admin mutation audit path:
  - `assistant.admin.report.closed`
  - existing domain event `assistant.report.closed` remains.

- Added review-flag admin mutation audit path:
  - `reviews.admin.flag.moderated`
  - existing domain event `reviews.flag.moderated` remains.

- Added notifications admin read-path audit events:
  - `notifications.admin.email_templates.viewed`
  - `notifications.admin.email_statistics.viewed`.

- Added market admin mutation audit paths for moderation actions:
  - `market.admin.report.moderated`
  - `market.admin.video_scan.moderated`
  - existing domain events `market.report.moderated` and `market.video_scan.moderated` remain.

- Added Phase 5 backend health-alert routing automation slice:
  - monitor task now sends email alerts on unhealthy/threshold-alert snapshots
  - cooldown dedupe added to prevent repeated noisy sends
  - configurable via `HEALTH_ALERT_NOTIFY_EMAIL_ENABLED`, `HEALTH_ALERT_NOTIFY_EMAIL_COOLDOWN_SECONDS`, `HEALTH_ALERT_RECIPIENTS`.

- Extended Phase 5 alert automation slice with webhook routing:
  - optional webhook channel support for unhealthy snapshots
  - cooldown dedupe for webhook alerts
  - configurable via `HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED`, `HEALTH_ALERT_WEBHOOK_URL`, `HEALTH_ALERT_NOTIFY_WEBHOOK_COOLDOWN_SECONDS`.

- Added Phase 3 product-video async lifecycle hardening slice:
  - scanner-unavailable fail-open keeps `security_scan_status=pending`
  - `scanned_at` now remains unset for retry states
  - added task-level lifecycle tests for clean/quarantined/fail-open/fail-closed paths.

- Added Phase 6 direct-upload callback hardening slice:
  - signed callback token replay is now rejected
  - callback object key must match product-scoped prefix
  - added tests for replay rejection and key-scope enforcement.

- Extended Phase 6 callback hardening:
  - callback now enforces allowed content-type values
  - callback is idempotent for already-recorded product+key uploads (returns existing record)
  - tests added for idempotency and content-type rejection.

- Added Phase 4 orders-refund admin mutation audit parity slice:
  - paired domain/admin events for refund process initiated/failed/rejected
  - paired domain/admin events for refund bulk decision applied
  - tests updated to assert paired event emission.

- Added Phase 4 notifications audit parity slice:
  - paired domain/admin events for email templates and statistics admin views
  - tests updated to assert paired event emission order.

- Added Phase 4 assistant observability audit parity slice:
  - paired domain/admin events for assistant logs/reports/metrics admin views
  - tests updated to assert paired event emission order.

- Added Phase 4 dashboard audit parity slice:
  - paired domain/admin events for overview/sales/products/orders/customers/analytics/company-ops read views
  - tests updated to assert paired event emission order for covered endpoints.

- Added Phase 4 orders seller read-path audit parity slice:
  - paired domain/admin events for seller-orders list and seller-order detail admin views
  - tests updated to assert paired emission order.


- Added Phase 4 cross-domain edge parity slice:
  - paired domain/admin events for market moderation queue reads:
    - `market.report.moderation_queue_viewed` / `market.admin.report.moderation_queue_viewed`
    - `market.video_scan.queue_viewed` / `market.admin.video_scan.queue_viewed`
  - paired domain/admin events for review moderation queue reads:
    - `reviews.flag.moderation_queue_viewed` / `reviews.admin.flag.moderation_queue_viewed`
  - paired domain/admin events for seller statistics admin reads:
    - `orders.seller.statistics_viewed` / `orders.admin.seller.statistics_viewed`
  - paired domain/admin events for staff evidence upload mutation paths:
    - `assistant.report.evidence_uploaded` / `assistant.admin.report.evidence_uploaded`
    - `assistant.report.evidence_validation_enqueue_failed` / `assistant.admin.report.evidence_validation_enqueue_failed`
  - tests updated/added to assert ordered domain→admin emission for covered paths.


- Added Phase 5 recovery-transition alert routing slice:
  - monitor task now sends recovery notifications when health state returns to healthy after prior unhealthy/degraded/error states
  - recovery notifications are sent over existing email/webhook channels and reuse channel cooldown controls
  - tests added for recovery notification send/no-send behavior.
- Added Phase 4 moderation-queue admin read audit parity slice:
  - paired domain/admin events for market report moderation queue views
  - paired domain/admin events for market video-scan queue views
  - paired domain/admin events for review-flag moderation queue views
  - tests updated to assert paired emission order.

- Added Phase 4 market product-create admin mutation audit parity slice:
  - paired domain/admin events for product creation by admin actors
  - existing seller product-create domain event remains unchanged
  - tests added to assert paired emission order for admin and domain-only behavior for sellers.

- Added Phase 4 market direct-upload-ticket admin mutation audit parity slice:
  - paired domain/admin events for direct-upload ticket issuance by admin actors
  - existing seller direct-upload ticket domain event remains unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for sellers.

- Added Phase 4 market direct-upload-callback admin mutation audit parity slice:
  - paired domain/admin events for verified direct-upload callbacks by admin actors
  - existing seller direct-upload callback domain event remains unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for sellers.

- Added Phase 4 market product-status admin mutation audit parity slice:
  - paired domain/admin events for mark-sold and reactivate actions by admin actors
  - existing seller product-status domain events remain unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for sellers.

- Added Phase 4 market product-image admin mutation audit parity slice:
  - paired domain/admin events for product-image upload and delete actions by admin actors
  - existing seller product-image domain events remain unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for sellers.

- Added Phase 4 market product-video-upload admin mutation audit parity slice:
  - paired domain/admin events for product-video uploads by admin actors
  - existing seller product-video upload domain event remains unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for sellers.

- Added Phase 4 orders seller-statistics admin read audit parity slice:
  - paired domain/admin events for seller statistics admin views
  - tests updated to assert paired emission order.

- Added Phase 4 assistant report/evidence admin mutation audit parity slice:
  - paired domain/admin events for staff report creation
  - paired domain/admin events for staff evidence uploads
  - paired domain/admin events for staff evidence-validation enqueue failures
  - tests added/updated for paired emission order (assistant test execution may require app-loading fixes in this environment).

- Added Phase 4 market report-create admin mutation audit parity slice:
  - paired domain/admin events for product-report creation by admin actors
  - existing non-admin report-create domain event remains unchanged
  - tests added to assert paired emission order for admins and domain-only behavior for non-admins.

## Next action
Continue Phase 5 alert-routing/incident automation maturity, in parallel with Phase 3 async malware lifecycle completion and Phase 6 storage hardening.
