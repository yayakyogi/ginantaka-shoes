# ADR 0001 — Monorepo with native tooling per app

**Status:** Accepted · **Date:** 2026-10-06

## Context
The project has three apps in three ecosystems (Python API, SvelteKit dashboard, Expo
mobile) plus a shared TypeScript API client. Most features touch more than one app
(a new API field shown in the dashboard and in mobile). One developer maintains it,
and AI agents work on it.

## Decision
One repository with `apps/` and `packages/`.

- Python: **uv** for `apps/api`.
- JavaScript/TypeScript: **Bun workspaces** for `apps/dashboard`, `apps/mobile`, `packages/*`.
  The linker is set explicitly in `bunfig.toml` (`isolated`), so Bun upgrades do not change
  install behavior silently. If an Expo/React Native package fails under isolated installs,
  switch to `hoisted` in a new ADR.
- **Taskfile.yml** at the root is the only command surface. Local runs, CI, and agents all
  use `task <name>`.
- PostgreSQL for local development runs in **Docker Compose** (`task db:up`).

## Alternatives considered
- **Separate repos per app.** Rejected: every API change becomes several PRs, and the
  generated API client would need publishing.
- **Turborepo / Nx / moon.** Deferred: the repo is small and polyglot. Revisit when CI time
  becomes a problem.
- **pnpm instead of Bun.** pnpm is the safer choice for Expo. Bun was chosen for install speed
  and one JS tool. Risk accepted and noted above.

## Consequences
- One clone, `task setup`, `task test`.
- Lockfiles (`uv.lock`, `bun.lock`) are never edited by hand.
- CI runs all suites on every change until path filtering is added.
