# ADR 0006 — Deployment on Cloudflare

**Status:** Proposed · **Date:** 2026-10-06

This ADR is not accepted yet. Nothing in the MVP may depend on a specific host.
Build the API as a standard FastAPI app runnable with uvicorn and Docker.

## Context
Portfolio budget: free tiers preferred. Cloudflare covers static hosting and R2.
Cloudflare made Python Workers generally available on 2026-09-21, with FastAPI support
through an ASGI connector and PostgreSQL access through Hyperdrive. It is new, runs on
Pyodide (not every package works), and Hyperdrive from Python Workers supports
synchronous SQLAlchemy only.

## Proposed decision
- **Dashboard:** static build (`adapter-static`) on Cloudflare (Workers static assets / Pages).
- **Images:** R2 (ADR 0004).
- **Database:** Neon free plan, separate from local Docker Postgres.
- **API, option A (preferred if the spike passes):** Cloudflare Python Workers + Hyperdrive → Neon.
- **API, option B (fallback):** Cloudflare Containers (requires the $5/month Workers Paid plan)
  or a small VPS, running the same Docker image.
- **Migrations** run from CI or locally against Neon, never from the Worker.

## Spike required before accepting (after MVP runs locally)
Deploy a throwaway Worker that proves all of these:
1. FastAPI app boots via the ASGI connector.
2. SQLModel sync session reads/writes Neon through Hyperdrive.
3. `pwdlib` Argon2 hash and verify work (or an alternative hasher is chosen, see ADR 0003).
4. `PyJWT` encode/decode works.
5. Presigned R2 URLs can be generated.
6. Cold-start latency is acceptable for a demo.

Any failure → option B.

## Consequences
- The code stays host-agnostic: configuration via environment variables only.
- Sync database access is a deliberate constraint from this ADR (see ADR 0002).
