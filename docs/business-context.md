# Business Context — Toko Sepatu (working name)

## What this is

A fullstack portfolio project: an online shoe store for a single Indonesian retailer.
It is built to demonstrate end-to-end product engineering across an API, an admin
dashboard, and a mobile app in one monorepo, with docs that let AI agents work on it
without guessing.

It is not a marketplace. There is exactly one store and one store owner.

## The store

- A single shoe retailer in Indonesia selling multiple brands (running, casual, etc.).
- Every shoe model comes in several sizes and sometimes several colors. Stock is held
  per size + color combination, not per model.
- Prices are in Indonesian Rupiah (IDR). There are no cents; money is always a whole number.
- Sizes use the EU system (for example 39, 40, 41).

## People

| Role | Who | Where they work | What they need |
|---|---|---|---|
| `owner` | The store owner (one account, created by seed script) | Admin dashboard (web) | Manage the catalog: products, variants, photos, categories, brands |
| `customer` | Shoppers | Mobile app | Browse the catalog, create an account, keep a cart |

Guests (not logged in) can browse the catalog on mobile. A cart requires an account.

## Language

- User-facing UI copy: Bahasa Indonesia.
- Code, docs, commit messages, API field names, error codes: English.

## MVP goal

A customer can open the mobile app, browse and search shoes, view a product with its
photos, sizes and colors, register or log in, and add specific variants to a cart.
The owner can fully manage that catalog from the dashboard.

Checkout and payment are deliberately not in the MVP. See `docs/prd.md` → Roadmap.

## Constraints

- Solo developer, portfolio budget: free tiers wherever possible.
- Must be demoable: mobile via Expo Go, dashboard via a public URL.
- Must be readable by reviewers: clean structure, tests, ADRs explaining decisions.
