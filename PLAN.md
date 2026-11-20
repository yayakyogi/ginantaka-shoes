# PLAN.md — Build order for the MVP

This file defines **the order** in which the MVP is built. What to build is defined in
`docs/prd.md` and the app PRDs; how it is built is constrained by `docs/adr/` and `AGENTS.md`.

## How to use this plan

- One phase per agent session. Start a session with:
  `Read AGENTS.md, PLAN.md, and docs/adr/. Execute Phase N only.`
- Do not start the next phase. Stop when the phase's done criteria pass and report:
  files created, AC IDs covered, anything skipped or unclear.
- **Human prerequisites** must be completed before the phase starts.
- After a phase is reviewed and merged, tag it: `git tag checkpoint/phase-N`.
- If a phase uncovers a gap in the PRD, stop and ask. Do not fill the gap by guessing.

## Status

| Phase | Name | Status |
|---|---|---|
| 0 | Scaffold | Done |
| 1 | API foundation + auth | Done |
| 2 | API owner catalog | Not started |
| 3 | API public catalog + cart | Not started |
| 4 | Dashboard | Not started |
| 5 | Mobile | Not started |
| 6 | Deployment spike | Not started |

Update this table at the end of each phase.

---

## Phase 0 — Scaffold

**Goal:** an empty but runnable monorepo. Every command in `AGENTS.md` works.
No product features: no endpoints, no screens, no tables.

### Human prerequisites
- Installed: git, uv, bun, node ≥ 20, task, Docker Desktop.

### Special rules for this phase
- There are no AC IDs in this phase. Do not implement any.
- Dependencies may be added **only** from this list, without asking:
  - API: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `alembic`, `psycopg[binary]`, `pyjwt`,
    `pwdlib[argon2]`, `boto3`, `pydantic-settings`, `email-validator`;
    dev: `pytest`, `httpx`, `ruff`.
  - Dashboard: whatever `sv create` generates for minimal + TypeScript + tailwindcss + vitest,
    plus `@sveltejs/adapter-static`, shadcn-svelte (via its official init), `@testing-library/svelte`,
    `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`.
  - Mobile: whatever `create-expo-app` (default template, Expo Router) generates, plus
    NativeWind (via its official install guide for the installed Expo SDK), `@tanstack/react-query`,
    `expo-secure-store`, `jest-expo`, `jest`, `@types/jest`, `@testing-library/react-native`.
  - API client: `openapi-fetch`; dev: `openapi-typescript`.
  - Anything else → ask.
- For shadcn-svelte and NativeWind, follow their current official docs. Do not copy config from
  memory; versions change.

### Deliverables
1. Root files: `package.json` (Bun workspaces: `apps/dashboard`, `apps/mobile`, `packages/*`),
   `bunfig.toml` (`linker = "isolated"`), `docker-compose.yml` (Postgres 16, databases `ginantaka_shoes`
   and `ginantaka_shoes_test` via `scripts/db-init.sql`), `Taskfile.yml`, `.gitignore`, `README.md`,
   `scripts/doctor.sh`, `.github/workflows/ci.yml`.
2. `apps/api`: uv project; folder layout from `apps/api/docs/prd.md` section 9;
   `app/core/config.py` (pydantic-settings reading every env var in PRD section 10);
   `app/core/db.py` (sync engine + session dependency); `app/main.py` with an empty FastAPI app
   (no routes) and CORS from `CORS_ORIGINS`; Alembic initialised in `migrations/` with
   `target_metadata = SQLModel.metadata` and the URL taken from settings, not `alembic.ini`;
   `app/scripts/export_openapi.py`; `tests/conftest.py` that connects to `TEST_DATABASE_URL`
   and wraps each test in a rolled-back transaction; `.env.example`.
3. `apps/dashboard`: SvelteKit with `adapter-static` (`fallback: 'index.html'`), `ssr = false`
   in `src/routes/+layout.ts`, Tailwind, shadcn-svelte initialised, Vitest configured with jsdom
   and `svelteTesting()`, `.env.example` with `PUBLIC_API_URL`.
4. `apps/mobile`: Expo app with Expo Router, NativeWind working on the default screen,
   Jest with `jest-expo` preset, `.env.example` with `EXPO_PUBLIC_API_URL`.
5. `packages/api-client` named `@ginantaka/api-client`: `src/index.ts` exporting `createApiClient(baseUrl)`
   built on `openapi-fetch`, plus generated `openapi.json` and `src/schema.d.ts`.
   Both apps depend on it with `workspace:*`.
6. Taskfile tasks: `setup`, `doctor`, `test`, `db:up`, `db:down`, `api:setup`, `api:dev`,
   `api:test`, `api:lint`, `api:migrate`, `api:migration`, `api:seed-owner`, `api:seed-demo`,
   `api:openapi`, `dashboard:dev`, `dashboard:test`, `dashboard:check`, `dashboard:build`,
   `mobile:dev`, `mobile:test`, `mobile:check`. `setup` copies each `.env.example` to `.env`
   only if `.env` does not exist. Seed tasks may point to scripts that do not exist yet.
7. Exactly one smoke test per app so test runners exit 0:
   API: `app.openapi()` returns the expected title. Dashboard: a trivial render test of the
   root page. Mobile: a trivial render test of the default screen.
   These are replaced by real tests in later phases.
8. CI: Postgres service, `task setup`, `task api:lint`, `task test`, and a check that
   `task api:openapi` leaves no git diff.

### Done criteria
- `task setup`, `task db:up`, `task test`, `task api:lint` all pass.
- `task --list-all` shows every task in deliverable 6.
- `task api:dev` serves `/docs`; `task dashboard:dev` serves a page; `task mobile:dev` opens in Expo Go
  (human check).
- `task api:openapi` produces no diff when run twice.
- No endpoint, table, screen, or AC was implemented.

---

## Phase 1 — API foundation + auth

**AC IDs:** AUTH-1 … AUTH-7, CMD-1.
**Tables:** `users`, `refresh_tokens`, `password_resets` (`docs/data-model.md`).

### Deliverables
1. Error handling (system PRD section 4.2): custom exception type with `code`, handlers that
   produce `{"code", "message"}`, and the `VALIDATION_ERROR` shape for 422s.
   Common errors from API PRD section 1.
2. `app/core/security.py`: pwdlib Argon2 hashing, JWT access tokens, opaque refresh tokens
   with SHA-256 hashing (ADR 0003).
3. `app/core/deps.py`: `get_current_user` and `require_role(*roles)`.
4. `EmailService` interface with a console backend (dev) and an in-memory fake (tests).
5. Models, first Alembic migration, auth router, `GET /me`.
6. `app/scripts/seed_owner.py` (CMD-1).
7. `task api:openapi` regenerated.

### Done criteria
- Every AUTH-* ID has tests, including the error codes listed for it.
- `require_role` has tests for 401 (no token, expired token) and 403 (wrong role) using a
  test-only route registered inside the test, not in the app.
- `task test` green, generated client committed.

---

## Phase 2 — API owner catalog

**AC IDs:** OCAT-1 … OCAT-4, OBRD-1 … OBRD-7, OPRD-1 … OPRD-5, OVAR-1 … OVAR-3, OIMG-1 … OIMG-5.
**Tables:** `categories`, `brands`, `products`, `product_variants`, `product_images`.

### Human prerequisites
- R2 bucket `ginantaka-shoes-dev` created, API token with read/write, values in `apps/api/.env`.
- R2 CORS rule allowing `PUT` from `http://localhost:5173` (needed in Phase 4, set it now).

### Deliverables
1. `StorageService` interface: presigned PUT URL, object exists (HEAD), delete, public URL
   builder. R2 implementation (boto3) and an in-memory fake for tests (ADR 0004).
2. Slug generation utility with collision suffixes.
3. Models + migration, including the partial unique index on `product_images`.
4. Owner routers. Business rules for images (default, ordering, promotion on delete) live in
   `services/images.py`, not in routers.

### Done criteria
- Every listed AC ID has tests. Every `/owner/*` endpoint has 401 and 403 (customer) tests.
- A test proves the database rejects two default images for one product.
- No test touches real R2.
- `task test` green, generated client committed.

---

## Phase 3 — API public catalog + cart

**AC IDs:** CAT-1 … CAT-4, CART-1 … CART-4, CMD-2.
**Tables:** `carts`, `cart_items`.

### Deliverables
1. Public catalog router (active products only, filters, pagination, `in_stock`,
   `default_image_url`).
2. Cart models + migration, cart service, cart router.
3. `app/scripts/seed_demo.py` (CMD-2): idempotent demo categories, brands, products, variants.

### Done criteria
- Every listed AC ID has tests. Every `/cart/*` endpoint has a 403 (owner) test.
- A test proves inactive products are invisible in CAT-3 and CAT-4.
- A test proves `subtotal_idr` excludes unavailable items.
- `task test` green, generated client committed. **The API is feature-complete for the MVP.**

---

## Phase 4 — Dashboard

Split into two sessions.

**4a — Auth, layout, categories, brands.** AC IDs: D-AUTH-1 … D-AUTH-7, D-CAT-1, D-CAT-2,
D-BRD-1, D-BRD-2, D-GEN-1 … D-GEN-3.
Includes: API client wrapper with token handling and single refresh retry, error-code → message
map, `formatRupiah`, protected layout with navigation.

**4b — Products, variants, images.** AC IDs: D-PRD-1 … D-PRD-5, D-VAR-1 … D-VAR-3,
D-IMG-1 … D-IMG-5.

### Human prerequisites
- `task api:seed-owner` run, API running locally, R2 CORS set (Phase 2).

### Done criteria (each session)
- Listed AC IDs covered by the tests described in the dashboard PRD section 4.
- `task dashboard:check` and `task dashboard:test` green.
- Human smoke test: log in as owner and exercise every listed AC in the browser.

---

## Phase 5 — Mobile

Split into two sessions.

**5a — Catalog and product detail (guest).** AC IDs: M-CAT-1 … M-CAT-6, M-PRD-1 … M-PRD-4,
M-GEN-1 … M-GEN-3.
Includes: API client wrapper, TanStack Query provider, `formatRupiah`, tab layout.

**5b — Auth and cart.** AC IDs: M-AUTH-1 … M-AUTH-6, M-PRD-5, M-PRD-6, M-CART-1 … M-CART-5.
Includes: secure token storage, single refresh retry, error-code → message map.

### Human prerequisites
- `task api:seed-demo` run, API reachable from the phone (`--host 0.0.0.0`, LAN IP in
  `EXPO_PUBLIC_API_URL`), at least a few products with images uploaded via the dashboard.

### Done criteria (each session)
- Listed AC IDs covered by the tests described in the mobile PRD section 4.
- `task mobile:check` and `task mobile:test` green.
- Human smoke test in Expo Go on a real device.

---

## Phase 6 — Deployment spike

**Goal:** decide ADR 0006. This phase produces a decision, not production infrastructure.

### Human prerequisites
- Cloudflare account, Neon project created.

### Deliverables
1. A throwaway Python Worker in `spikes/python-worker/` (deleted or kept out of `apps/` after
   the decision) testing the six points listed in ADR 0006.
2. A short report in `spikes/python-worker/RESULT.md`: pass/fail per point, cold-start numbers.
3. A proposed update to ADR 0006 (Accepted with option A or B). The human accepts it.

### Done criteria
- ADR 0006 status changed by the human, not by the agent.
- Nothing in `apps/` changed.

---

## After the MVP

Roadmap items in `docs/prd.md` section 6 each get their own PRD update and a new phase
appended here. Never extend an existing phase.
