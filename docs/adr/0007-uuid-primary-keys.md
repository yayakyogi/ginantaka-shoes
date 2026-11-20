# ADR 0007 — UUID primary keys

**Status:** Accepted · **Date:** 2026-10-07

Requested and accepted by the project owner during Phase 1, before any migration was shipped.

## Context
`docs/data-model.md` originally used `bigint identity` ids. Sequential ids appear in every
URL the clients call (`/owner/products/42`, `/cart/items/7`), which reveals counts
(how many users, products, cart items exist) and makes ids guessable.

## Decision
- Every table's `id` is a `uuid` primary key, **UUIDv4**. Foreign keys are `uuid`.
- The API generates ids in Python (`uuid.uuid4()`), so an id is known before the row is
  flushed. The column also has `DEFAULT gen_random_uuid()` (built into PostgreSQL 13+) for
  rows inserted outside the app.
- In JSON and OpenAPI, ids are strings with `format: uuid`. The JWT `sub` claim is the
  user's UUID as a string.
- Ids carry no order. Code must never sort by `id` to mean "newest"; use `created_at`.
- Any sort on `created_at` adds `id` as a tie-breaker (`ORDER BY created_at DESC, id DESC`).
  `created_at` defaults to `now()`, the transaction start time, so rows inserted in one
  transaction (e.g. `seed-demo`) share it; without the tie-breaker, offset pagination can
  repeat or skip rows.
- Id path parameters are typed `UUID`. A malformed id → `422 VALIDATION_ERROR`; a well-formed
  id that does not exist → the endpoint's `404` code.

## Alternatives considered
- **Keep `bigint identity`.** Smallest and fastest, but leaks counts and is guessable.
- **UUIDv7 (time-ordered).** Better index locality and sortable, but neither Python 3.12 nor
  PostgreSQL 16 can generate it without a new dependency. Not worth it at this scale.
  Revisit on Python 3.14 / PostgreSQL 18, which generate v7 natively.
- **bigint id internally plus a public UUID column.** Two ids per row to keep in sync.

## Consequences
- 16-byte keys instead of 8; random inserts spread across the index. Irrelevant for one shop.
- "Newest first" sorting (e.g. CAT-3) must use `created_at DESC, id DESC`, not `id` alone.
- Client code treats ids as opaque strings.
