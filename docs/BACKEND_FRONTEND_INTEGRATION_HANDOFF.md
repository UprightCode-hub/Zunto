# Backend → Frontend Integration Handoff (Condensed)

_Last updated: 2026-02-22 (UTC)_

This file was condensed to remove duplicated narrative.

## Canonical file
Use `docs/NEXT_SESSION_EXECUTION_BRIEF.md` as the single source for:
- pending backend/frontend parity work,
- admin portal integration status,
- endpoint/audit naming synchronization,
- next chunk execution checklist.

## Current parity baseline (kept here for quick reference)
- Product report moderation queue/actions: wired.
- Review flag moderation queue/actions: wired.
- Bulk refund decision controls: wired.
- Ops queues pagination/filtering: wired.
- Orders item status mutation emits:
  - `orders.item.status_updated`
  - `orders.admin.order_item_status_updated` (admin actor path)

For all follow-ups, update only the canonical brief.
