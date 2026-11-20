# ADR 0005 — OpenAPI as the contract, generated TypeScript client

**Status:** Accepted · **Date:** 2026-10-06

## Context
Two TypeScript clients consume one Python API. Hand-written types drift from the API.

## Decision
- FastAPI's OpenAPI schema is the contract. Every endpoint has typed request and response
  models, so the schema is complete.
- `task api:openapi`:
  1. Exports the schema to `packages/api-client/openapi.json` (script, no running server).
  2. Runs `openapi-typescript` to generate `packages/api-client/src/schema.d.ts`.
- `packages/api-client` exports a configured `openapi-fetch` client factory and the types.
  Both clients import from `@toko/api-client`. Generated files are committed.
- CI runs `task api:openapi` and fails if it produces a git diff.

## Alternatives considered
- **Hand-written `packages/shared` types.** Rejected: drift is guaranteed.
- **Full SDK generators (orval, hey-api).** More features, more generated code to review.
  `openapi-fetch` is small and enough for the MVP.

## Consequences
- Changing an API response shape breaks client type-checks immediately, which is the point.
- Agents must run `task api:openapi` after any API schema change.
