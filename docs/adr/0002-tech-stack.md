# ADR 0002 — Technology stack per app

**Status:** Accepted · **Date:** 2026-10-06

## Context
Portfolio project. The stack should be modern, easy to explain in an interview, and cheap
to run. Each choice below is the default; anything else needs a new ADR.

## Decision

### API (`apps/api`)
- Python 3.12, FastAPI.
- SQLModel on SQLAlchemy, **synchronous** sessions (see ADR 0006 for why sync).
- Alembic for migrations. Every schema change ships with a migration.
- PostgreSQL 16 (Docker locally, Neon when deployed).
- Password hashing: `pwdlib` with Argon2 (see ADR 0003).
- JWT: `PyJWT`.
- Object storage: `boto3` against the R2 S3-compatible API.
- Tests: pytest against a real PostgreSQL test database, not SQLite, because the schema
  uses PostgreSQL-only features (partial unique index).
- Lint/format: ruff. Type hints everywhere.

### Dashboard (`apps/dashboard`)
- SvelteKit with `adapter-static` and `ssr = false` (pure SPA, no server code).
- `+page.ts` load functions for data. No `+page.server.ts` or `+server.ts`.
- shadcn-svelte for UI components, Tailwind CSS.
- Vitest + @testing-library/svelte, svelte-check.

### Mobile (`apps/mobile`)
- Expo with Expo Router (file-based routes). Runs in Expo Go for the MVP.
- NativeWind for styling.
- TanStack Query for server state.
- `expo-secure-store` for tokens.
- Jest with `jest-expo` + @testing-library/react-native. Not Vitest: the React Native
  ecosystem is built on Jest.

### Shared (`packages/api-client`)
- `openapi-typescript` generated types + `openapi-fetch` as the HTTP client (ADR 0005).

## Alternatives considered
- **Async SQLAlchemy.** Rejected for now: adds complexity, and the deploy target being
  evaluated supports sync only.
- **Full SvelteKit (SSR + server routes).** Rejected: FastAPI is the only backend; a second
  server layer adds deploy cost without benefit for an internal dashboard.
- **Flutter for mobile.** Rejected: sharing TypeScript types with the dashboard is a key
  benefit of this monorepo.

## Consequences
- Two JS test runners (Vitest, Jest). Taskfile hides the difference.
- Adding a runtime dependency to any app requires asking first (see `AGENTS.md`).
