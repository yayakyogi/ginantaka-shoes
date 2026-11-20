# PRD — Toko Sepatu MVP (system level)

This is the top-level product spec. Each app has its own PRD with details:

- API: `apps/api/docs/prd.md`
- Dashboard: `apps/dashboard/docs/prd.md`
- Mobile: `apps/mobile/docs/prd.md`

Data model: `docs/data-model.md` · Decisions: `docs/adr/` · Context: `docs/business-context.md`

**Rule for agents and humans:** if a feature is not listed in this file or an app PRD,
it is out of scope. Ask before building it.

## 1. Applications

| App | Path | Stack | Users |
|---|---|---|---|
| API | `apps/api/` | Python 3.12 · FastAPI · SQLModel · Alembic · PostgreSQL | Both clients |
| Dashboard | `apps/dashboard/` | SvelteKit (SPA mode) · shadcn-svelte · Vitest | `owner` |
| Mobile | `apps/mobile/` | Expo (React Native) · Expo Router · NativeWind · Jest | Guests, `customer` |
| API client | `packages/api-client/` | TypeScript types generated from the API's OpenAPI schema | Dashboard, Mobile |

The API is the single source of truth for data, prices, stock, and authorization.
Clients never compute prices or enforce permissions on their own.

## 2. Roles

| Role | How the account is created | Can log in to | Permissions |
|---|---|---|---|
| `owner` | Seed command only (`task api:seed-owner`) | Dashboard | Full catalog management |
| `customer` | Self-registration in the mobile app | Mobile | Own profile and own cart |
| Guest | — | — | Read the public catalog |

- One account has exactly one role.
- Exactly one owner exists in the MVP.
- Every role check in the API goes through a single dependency (`require_role`). See ADR 0003.

## 3. MVP features

### F1. Authentication
- Customer register (mobile).
- Login for both roles (customer on mobile, owner on dashboard).
- Token refresh and logout.
- Forgot password via a 6-digit code sent by email, entered in the app.

### F2. Catalog management (owner, dashboard)
- CRUD categories.
- CRUD brands, each with an optional logo image.
- CRUD products with name, description, price, category, brand, active flag.
- CRUD variants per product (EU size + color + SKU + stock).
- Up to 5 photos per product, with a default photo and a gallery order.

### F3. Catalog browsing (guest and customer, mobile)
- List active products with search, category filter, and brand filter.
- Product detail with photos, sizes, colors, and stock availability.
- List categories and brands.

### F4. Cart (customer, mobile)
- One cart per customer.
- Add a variant with a quantity, change quantity, remove an item.
- See cart subtotal.

## 4. Cross-cutting rules

1. **Money** is integer IDR in every layer. No floats, no decimals. Field names end in `_idr`.
2. **Errors** always have a body `{"code": "...", "message": "..."}`. Clients switch on `code`,
   never on `message`. Codes are listed in `apps/api/docs/prd.md`.
3. **Sizes** are EU, stored as integers.
4. **Images** are stored in object storage (Cloudflare R2). The database stores object keys,
   not full URLs. See ADR 0004.
5. **Types** shared between API and clients are generated from OpenAPI, never hand-written.
   See ADR 0005.
6. **Time** is stored in UTC (`timestamptz`).

## 5. Out of scope for MVP

Do not build any of these without a PRD update:

- Checkout, orders, payment, shipping cost, invoices.
- Discounts, vouchers, promotions.
- Google login or any social login.
- Email verification.
- Changing password while logged in, editing profile, deleting account.
- Wishlist, reviews, ratings.
- Multiple stores, store staff, RBAC with granular permissions.
- Push notifications.
- Stock reservation (adding to cart does not reserve stock).
- Rate limiting and account lockout (known risk, see Roadmap).
- Publishing to App Store / Play Store (MVP runs in Expo Go).
- Analytics dashboard, reports.

## 6. Roadmap (after MVP, not to be built now)

1. Checkout with Midtrans Sandbox (orders, order lines with price snapshots, payment status).
2. Rate limiting on auth endpoints.
3. Email verification.
4. Google login.
5. RBAC: `roles`, `permissions`, `user_roles` tables replacing `users.role`.
6. TestFlight and Google Play internal testing builds via EAS.
7. Deployment per ADR 0006.

## 7. Definition of done (any MVP task)

- Covered by tests written before or with the implementation.
- `task test` passes.
- New API endpoints are listed in `apps/api/docs/prd.md` and referenced by an acceptance criterion.
- Generated API client is up to date (`task api:openapi` produces no diff).
- No item from section 5 was added.
