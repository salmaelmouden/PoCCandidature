# Application package

Phase 1 delivers the **data foundation** under `app/db/`.

Later phases add: `api/`, `analytics/`, `agents/`, `skills/`, dashboard adapters.

Rule: business logic stays out of UI; agents use skills/repositories only.
