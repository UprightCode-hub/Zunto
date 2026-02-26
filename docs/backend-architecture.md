# Backend Architecture

## Scope

This document defines the backend architecture for recommendation session management and behavior telemetry implemented in Phase 8. It describes persisted conversation context, category drift handling, demand gap capture, interaction source tracking, and behavior aggregation.

## Core Domain Components

### Conversation Session (assistant app)

`ConversationSession` is the state anchor for both support and recommendation flows.

**Phase 8 fields**
- `context_type`: distinguishes support vs recommendation contexts.
- `active_product`: current top product bound to an active recommendation journey.
- `constraint_state`: structured constraints extracted from user prompts.
- `intent_state`: intent memory and pending switch metadata.
- `drift_flag`: explicit drift marker when category intent changes.
- `completed_at`: lifecycle completion timestamp for closed recommendation threads.

**Operational notes**
- Recommendation sessions are initialized with deterministic context defaults before evaluation.
- Session indexing supports retrieval by context and recency for recommendation workloads.

### Recommendation Demand Gap (assistant app)

`RecommendationDemandGap` persists unmet recommendation demand using:
- `requested_category`
- `requested_attributes`
- `user_location`
- `frequency`
- first/last seen timestamps

Records are keyed by `(user, requested_category, requested_attributes, user_location)` via application-level `get_or_create` semantics and frequency increments on repeated misses.

### User Behavior Profile (assistant app)

`UserBehaviorProfile` stores aggregated metrics used by recommendation optimization:
- AI and non-AI search counts
- dominant category signals
- average budget envelope
- AI and non-AI conversion rates
- drift/switch frequency
- high-intent/no-conversion risk flag
- last aggregation timestamp

### Product View Source Tracking (market app)

`ProductView.source` classifies view origin using constrained values:
- `ai`
- `normal_search`
- `homepage_feed`
- `direct`

Request-level source parsing is normalized in the product detail tracking flow, and invalid values fall back to `direct`.

## Model Relationships

- `ConversationSession.user -> AUTH_USER_MODEL` (`SET_NULL`)
- `ConversationSession.active_product -> market.Product` (`SET_NULL`)
- `RecommendationDemandGap.user -> AUTH_USER_MODEL` (`SET_NULL`)
- `UserBehaviorProfile.user -> AUTH_USER_MODEL` (`OneToOne`)
- `ProductView.user -> AUTH_USER_MODEL` (`SET_NULL`)
- `ProductView.product -> market.Product` (`CASCADE`)

These relationships ensure recommendation sessions, unmet demand, and interaction telemetry can be correlated by user and product dimensions without hard deletes on user deactivation.

## Session Lifecycle (Recommendation Context)

1. **Initialization**
   - Recommendation mode invokes context initialization.
   - Session is normalized to recommendation context and structured state containers.

2. **Constraint Extraction**
   - Incoming message is parsed into category, budget, attributes, location, intent.
   - Extracted constraints merge with prior known state.

3. **Drift Evaluation**
   - If category changes from previous constraint state:
     - set `drift_flag = true`
     - store pending switch payload in `intent_state.pending_category_switch`
     - return confirmation response

4. **Switch Confirmation Path**
   - On explicit confirmation token:
     - current session is closed (`current_state=closed`, `completed_at` set)
     - new recommendation session is created with inherited metadata and pending constraints
     - drift marker is cleared on source session

5. **Recommendation Resolution Path**
   - If no drift transition is required:
     - constraint and intent state are persisted
     - matching products are queried
     - `active_product` is set when a match exists

6. **Unmet Demand Path**
   - If no product match exists:
     - demand gap record is created or frequency incremented

## Drift Flow

- Drift detection is category-to-category transition based on structured constraint state.
- Drift does not overwrite or discard historical thread context.
- New category journeys are isolated in newly created recommendation sessions only after explicit user confirmation.
- Previous session remains auditable and lifecycle-complete with `completed_at`.

## Demand Gap Logging Strategy

- Demand gap logging is executed only on recommendation miss.
- Logged dimensions: category, attributes, location, user.
- Repeat misses for same signature increment `frequency`.
- Scheduled cleanup removes stale demand gap rows older than retention threshold (90 days).

## Source Tracking Design

- Product detail view tracking writes `ProductView` with normalized source value.
- Source taxonomy supports AI adoption analysis and baseline comparison with manual discovery pathways.
- Source field is indexed for reporting by channel and recency.

## Behavior Aggregation Design

A scheduled aggregation task computes per-user profile metrics from:
- recommendation sessions (`ConversationSession`)
- product view telemetry (`ProductView.source`)
- cart events (`CartEvent.data.source`)

Derived outcomes include:
- AI-to-cart conversion rate
- normal-search conversion rate
- drift/switch frequency
- category and budget tendencies
- high-intent/no-conversion flagging for intervention analysis

## Schema and Migration Alignment

Phase 8 schema changes are represented by:
- `assistant/migrations/0014_recommendation_context_and_profiles.py`
  - adds recommendation session fields and indexes
  - creates `RecommendationDemandGap`
  - creates `UserBehaviorProfile`
- `market/migrations/0009_productview_source.py`
  - adds `ProductView.source`
  - adds source/time index

Current model definitions in `assistant.models` and `market.models` align with these migration artifacts.

## Reviewed Implementation Map

- Session model + Phase 8 fields: `assistant/models.py`
- Recommendation orchestration, drift handling, thread switching, demand gap logging: `assistant/services/recommendation_service.py`
- Recommendation invocation in chat flow: `assistant/processors/conversation_manager.py`
- Behavior profile and demand gap aggregation tasks: `assistant/tasks.py`
- Product source field and indexing: `market/models.py`
- Source normalization and view-write path: `market/views.py`
- Migration artifacts: `assistant/migrations/0014_recommendation_context_and_profiles.py`, `market/migrations/0009_productview_source.py`
- Verification tests: `assistant/tests_recommendation_phase8.py`

## Consistency Review Result

No code-level inconsistency was found between Phase 8 model definitions, orchestration logic, and migration artifacts in the reviewed scope.
