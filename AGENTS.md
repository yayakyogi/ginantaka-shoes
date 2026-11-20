# Toko Sepatu

Single-store shoe e-commerce: FastAPI API, SvelteKit dashboard (owner), Expo mobile app (customer).
Context: docs/business-context.md · Spec: docs/prd.md · Data: docs/data-model.md · Decisions: docs/adr/
Per-app specs: apps/api/docs/prd.md · apps/dashboard/docs/prd.md · apps/mobile/docs/prd.md
Build order: PLAN.md

## Before any task
0. Read PLAN.md and work only inside the phase you were asked to execute.
   Phase exceptions (nothing else is exempt):
   - Phase 0 (scaffold) has no AC IDs. Its rules in PLAN.md replace step 2 below, the
     "ask before adding a task" rule, and rule #9 (dependencies). It may create .github/workflows/ci.yml.
   - Phase 6 (deployment spike) may write host-specific code, but only under spikes/.
1. Read docs/prd.md and the PRD of every app you will touch.
2. Find the acceptance criterion ID (e.g. `CART-2`, `D-IMG-3`) the task implements.
   No ID → the work is out of scope. Stop and ask.
3. Read docs/adr/ before proposing any architectural change.

## Commands
Use only commands defined in Taskfile.yml (`task --list-all`). Never invent commands.
If a needed task does not exist yet, ask before adding it.

`task setup` · `task test` · `task db:up` · `task api:dev` · `task api:test` · `task api:migrate`
`task api:openapi` · `task dashboard:dev` · `task dashboard:test` · `task mobile:dev` · `task mobile:test`

## Non-negotiable rules
1. Write or update tests BEFORE implementation. Never claim done without `task test` green.
2. Money is integer IDR. No floats. Fields end in `_idr`. Clients never calculate prices.
3. Every API error body is `{"code", "message"}`. Clients map `code`, never parse `message`.
4. Role checks only through `require_role`. Never compare `user.role` in a handler.
5. Every `/owner/*` endpoint has 401 and 403 tests. Every `/cart/*` endpoint has a 403 test for owners.
6. Schema change → Alembic migration in the same change, and docs/data-model.md updated.
7. API response change → run `task api:openapi` and commit the regenerated client.
8. Never hand-edit uv.lock, bun.lock, or anything under packages/api-client/src/schema.d.ts.
9. Ask before adding any new dependency.
10. Store image object keys, never full URLs.

## Scope guard
docs/prd.md section 5 lists what is out of scope (checkout, payment, social login, RBAC,
email verification, rate limiting, etc.). Do not build, stub, or "prepare" any of it,
even if it seems small or helpful. Suggest it as a follow-up instead.

## Conventions
Python: type hints, ruff, pytest `test_<behavior>`, AC ID in each test docstring.
Svelte: Svelte 5 runes, TypeScript strict, no `any`, shadcn-svelte components.
React Native: function components, TypeScript strict, no `any`, NativeWind classes.
UI copy: Bahasa Indonesia. Code, docs, commits: English.
Commits: conventional (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), one AC group per commit where possible.

## Out of bounds for agents
Do not modify .github/, secrets, `.env` files, or any ADR with status Accepted.
Propose a new ADR instead. ADR 0006 is Proposed: do not build host-specific code.
