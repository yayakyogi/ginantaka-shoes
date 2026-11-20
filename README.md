# Ginantaka Shoes

Single-store shoe e-commerce: FastAPI API, SvelteKit dashboard (owner), Expo mobile app (customer).

| Path | What |
|---|---|
| `apps/api` | Python 3.12 · FastAPI · SQLModel · Alembic · PostgreSQL 16 |
| `apps/dashboard` | SvelteKit SPA · shadcn-svelte · Tailwind · Vitest |
| `apps/mobile` | Expo · Expo Router · NativeWind · Jest |
| `packages/api-client` | `@ginantaka/api-client`, generated from the API's OpenAPI schema |

Specs: `docs/prd.md` and `apps/*/docs/prd.md` · Data: `docs/data-model.md` ·
Decisions: `docs/adr/` · Build order: `PLAN.md` · Agent rules: `AGENTS.md`

## Prerequisites

git, [uv](https://docs.astral.sh/uv/), [bun](https://bun.sh), node ≥ 20,
[task](https://taskfile.dev), Docker Desktop. Check with `task doctor`.

## Getting started

```sh
task setup     # install deps, create .env files from .env.example
task db:up     # start Postgres (databases ginantaka_shoes, ginantaka_shoes_test)
task test      # run every test suite
```

Run the apps:

```sh
task api:dev        # http://localhost:8000/docs
task dashboard:dev  # http://localhost:5173
task mobile:dev     # scan the QR code with Expo Go
```

`task --list-all` shows every command. Taskfile.yml is the only command surface.
