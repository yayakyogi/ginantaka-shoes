# PRD — API (`apps/api`)

System PRD: `docs/prd.md` · Data model: `docs/data-model.md` · Auth: ADR 0003 · Images: ADR 0004

Every endpoint below has an acceptance criterion ID (e.g. `AUTH-3`). Tests reference these
IDs in their docstring. An endpoint not listed here must not exist.

## 1. Conventions

- Base path: `/` (no version prefix in the MVP). JSON only.
- Auth header: `Authorization: Bearer <access_token>`.
- **Ids** are UUIDv4 strings (ADR 0007). A malformed id in the path → `422 VALIDATION_ERROR`;
  a well-formed unknown id → the endpoint's `404` code.
- **Error body:** `{"code": "SOME_CODE", "message": "Human readable"}`.
- **Validation errors (422):**
  `{"code": "VALIDATION_ERROR", "message": "...", "fields": [{"field": "email", "message": "..."}]}`.
  FastAPI's default `{"detail": ...}` shape is replaced by a custom handler.
- **Pagination:** query `limit` (default 20, max 100) and `offset` (default 0).
  Response: `{"items": [...], "total": 123, "limit": 20, "offset": 0}`.
- **Money:** `*_idr` fields are integers.
- **Images in responses:** `{"id", "url", "position", "is_default"}`, where `url` is built from
  `PUBLIC_ASSET_BASE_URL` + `object_key`.

### Common errors (any endpoint)
| Status | Code | When |
|---|---|---|
| 401 | `UNAUTHENTICATED` | Missing, malformed, or expired access token |
| 403 | `FORBIDDEN` | Valid token, wrong role |
| 404 | `NOT_FOUND` | Unknown route or resource without a specific code |
| 422 | `VALIDATION_ERROR` | Request body or query fails validation |

## 2. Auth

| ID | Endpoint | Auth | Behaviour |
|---|---|---|---|
| AUTH-1 | `POST /auth/register` | — | Body `{email, password, name}`. Creates a `customer`. Returns `201` with `{user, access_token, refresh_token}`. Duplicate email → `409 EMAIL_ALREADY_REGISTERED`. Password < 8 or > 128 chars → `422`. |
| AUTH-2 | `POST /auth/login` | — | Body `{email, password}`. Returns `200` with `{user, access_token, refresh_token}`. Wrong email or password → `401 INVALID_CREDENTIALS` (same code for both). |
| AUTH-3 | `POST /auth/refresh` | — | Body `{refresh_token}`. Revokes it and returns a new pair. Revoked, expired, or unknown → `401 REFRESH_TOKEN_INVALID`. |
| AUTH-4 | `POST /auth/logout` | — | Body `{refresh_token}`. Revokes it. Always `204`, even if already revoked. |
| AUTH-5 | `GET /me` | any role | Returns `{id, email, name, role}`. |
| AUTH-6 | `POST /auth/password/forgot` | — | Body `{email}`. Always `202`. If the user exists, invalidates older codes and sends a new 6-digit code (logged to console in dev). |
| AUTH-7 | `POST /auth/password/reset` | — | Body `{email, code, new_password}`. On success: updates password, marks code used, revokes all refresh tokens, `204`. Wrong code → `400 RESET_CODE_INVALID` and increments attempts. Expired or used → `400 RESET_CODE_EXPIRED`. 5 failed attempts → `429 RESET_TOO_MANY_ATTEMPTS` (code is dead, request a new one). Unknown email → `400 RESET_CODE_INVALID`. |

`user` object everywhere: `{id, email, name, role}`. Emails are compared lowercase.

## 3. Public catalog

| ID | Endpoint | Auth | Behaviour |
|---|---|---|---|
| CAT-1 | `GET /categories` | — | All categories `{id, name, slug}`, sorted by name. Not paginated. |
| CAT-2 | `GET /brands` | — | All brands `{id, name, slug, logo_url}` (`logo_url` null if none), sorted by name. Not paginated. |
| CAT-3 | `GET /products` | — | Paginated, **active products only**. Query: `q` (case-insensitive match on name), `category` (slug), `brand` (slug). Item: `{id, name, slug, price_idr, brand, category, default_image_url, in_stock}`. `in_stock` is true if any variant has stock > 0. Sorted newest first (`created_at` desc, then `id` desc, ADR 0007). Unknown category/brand slug → empty list, not an error. |
| CAT-4 | `GET /products/{slug}` | — | Active product detail: list fields plus `description`, `images` (by `position`), `variants` `{id, size_eu, color, stock}` sorted by size then color. Inactive or unknown → `404 PRODUCT_NOT_FOUND`. |

## 4. Owner — categories and brands

All require role `owner`.

| ID | Endpoint | Behaviour |
|---|---|---|
| OCAT-1 | `GET /owner/categories` | Same as CAT-1 plus `product_count`. |
| OCAT-2 | `POST /owner/categories` | Body `{name}`. `201`. Duplicate name (case-insensitive) → `409 CATEGORY_NAME_TAKEN`. |
| OCAT-3 | `PATCH /owner/categories/{id}` | Body `{name}`. Slug regenerates. Same duplicate rule. Unknown → `404 CATEGORY_NOT_FOUND`. |
| OCAT-4 | `DELETE /owner/categories/{id}` | `204`. Has products → `409 CATEGORY_IN_USE`. |
| OBRD-1 | `GET /owner/brands` | Same as CAT-2 plus `product_count`. |
| OBRD-2 | `POST /owner/brands` | Body `{name}`. `201`. Duplicate → `409 BRAND_NAME_TAKEN`. |
| OBRD-3 | `PATCH /owner/brands/{id}` | Body `{name}`. Unknown → `404 BRAND_NOT_FOUND`. |
| OBRD-4 | `DELETE /owner/brands/{id}` | `204`, also deletes logo object. Has products → `409 BRAND_IN_USE`. |
| OBRD-5 | `POST /owner/brands/{id}/logo/upload-url` | Body `{content_type, size_bytes}`. Returns `{upload_url, object_key, expires_in}`. Bad type → `422 UNSUPPORTED_IMAGE_TYPE`. Over 2 MB → `422 IMAGE_TOO_LARGE`. |
| OBRD-6 | `PUT /owner/brands/{id}/logo` | Body `{object_key}`. Key must start with `brands/{id}/` and exist in storage, else `422 INVALID_OBJECT_KEY`. Replaces `logo_key`, deletes old object. Returns brand. |
| OBRD-7 | `DELETE /owner/brands/{id}/logo` | Clears `logo_key`, deletes object. `204`. |

## 5. Owner — products and variants

All require role `owner`. Unknown product id → `404 PRODUCT_NOT_FOUND`.

| ID | Endpoint | Behaviour |
|---|---|---|
| OPRD-1 | `GET /owner/products` | Paginated, **includes inactive**. Query: `q`, `category`, `brand`, `is_active`. Item adds `is_active`, `variant_count`, `total_stock`. |
| OPRD-2 | `POST /owner/products` | Body `{name, description?, price_idr, category_id, brand_id, is_active?}`. `201`. Unknown category/brand → `422 CATEGORY_NOT_FOUND` / `422 BRAND_NOT_FOUND`. `price_idr` must be > 0. Slug generated, unique. |
| OPRD-3 | `GET /owner/products/{id}` | Full detail, including inactive, with images and variants. |
| OPRD-4 | `PATCH /owner/products/{id}` | Partial update of the OPRD-2 fields. Changing name regenerates slug. |
| OPRD-5 | `DELETE /owner/products/{id}` | Hard delete; cascades variants, images, and cart items. Deletes image objects. `204`. |
| OVAR-1 | `POST /owner/products/{id}/variants` | Body `{size_eu, color, sku, stock}`. `201`. Duplicate size+color in product → `409 VARIANT_EXISTS`. Duplicate SKU → `409 SKU_TAKEN`. |
| OVAR-2 | `PATCH /owner/variants/{variant_id}` | Partial update of OVAR-1 fields, same rules. Unknown → `404 VARIANT_NOT_FOUND`. |
| OVAR-3 | `DELETE /owner/variants/{variant_id}` | `204`. Cascades cart items. |

## 6. Owner — product images

All require role `owner`. Rules from `docs/data-model.md` → product_images.

| ID | Endpoint | Behaviour |
|---|---|---|
| OIMG-1 | `POST /owner/products/{id}/images/upload-url` | Body `{content_type, size_bytes}`. Already 5 images → `409 IMAGE_LIMIT_REACHED`. Bad type → `422 UNSUPPORTED_IMAGE_TYPE`. Over 5 MB → `422 IMAGE_TOO_LARGE`. |
| OIMG-2 | `POST /owner/products/{id}/images` | Body `{object_key}`. Validates prefix and existence (`422 INVALID_OBJECT_KEY`). Appends at the last position. First image of the product becomes default. Re-checks the 5-image limit. `201` with the image. |
| OIMG-3 | `PATCH /owner/products/{id}/images/{image_id}/default` | Makes this image the only default, in one transaction. Returns all images. Image not in product → `404 IMAGE_NOT_FOUND`. |
| OIMG-4 | `PATCH /owner/products/{id}/images/order` | Body `{image_ids: [...]}`, must contain exactly the product's image ids, else `422 INVALID_IMAGE_ORDER`. Rewrites positions 0..n-1. Does not change default. |
| OIMG-5 | `DELETE /owner/products/{id}/images/{image_id}` | Deletes, re-numbers positions, promotes the lowest-position image if the default was deleted, deletes the object. `204`. |

## 7. Cart

All require role `customer`. The cart is created on first access.

| ID | Endpoint | Behaviour |
|---|---|---|
| CART-1 | `GET /cart` | `{items: [...], subtotal_idr}`. Item: `{id, quantity, variant: {id, size_eu, color, stock}, product: {id, name, slug, price_idr, default_image_url}, available, line_total_idr}`. `available` is false if the product is inactive or `quantity > stock`. `subtotal_idr` sums `line_total_idr` of available items only. |
| CART-2 | `POST /cart/items` | Body `{variant_id, quantity}` (quantity ≥ 1). Existing variant in cart → quantities add up. Resulting quantity > stock → `409 INSUFFICIENT_STOCK`. Inactive product → `409 PRODUCT_UNAVAILABLE`. Unknown variant → `404 VARIANT_NOT_FOUND`. Returns the cart. |
| CART-3 | `PATCH /cart/items/{item_id}` | Body `{quantity}` (≥ 1). Same stock rule. Item not in this user's cart → `404 CART_ITEM_NOT_FOUND`. Returns the cart. |
| CART-4 | `DELETE /cart/items/{item_id}` | Removes the item. Returns the cart. Same 404 rule. |

Stock is checked, not reserved.

## 8. Commands (not endpoints)

| ID | Command | Behaviour |
|---|---|---|
| CMD-1 | `task api:seed-owner` | Creates the owner from env vars `OWNER_EMAIL`, `OWNER_PASSWORD`, `OWNER_NAME`. Fails if an owner already exists. |
| CMD-2 | `task api:seed-demo` | Inserts demo categories, brands, and products with variants (no images). Idempotent. Dev only. |

## 9. Structure

```
apps/api/
├── app/
│   ├── main.py            # FastAPI app, error handlers, routers
│   ├── core/              # config, db session, security (jwt, hashing), errors, deps (require_role)
│   ├── models/            # SQLModel tables
│   ├── schemas/           # request/response models (when they differ from tables)
│   ├── routers/           # auth, catalog, owner_*, cart
│   ├── services/          # business logic (images, cart, auth), storage, email
│   └── scripts/           # seed_owner, seed_demo, export_openapi
├── migrations/            # Alembic
└── tests/                 # mirrors routers; one file per AC group
```

Routers stay thin: validation and HTTP mapping only. Logic lives in `services/`.

## 10. Configuration (env vars)

`DATABASE_URL`, `TEST_DATABASE_URL` (tests only), `JWT_SECRET`, `ACCESS_TOKEN_TTL_MINUTES` (15), `REFRESH_TOKEN_TTL_DAYS` (30),
`CORS_ORIGINS`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`,
`PUBLIC_ASSET_BASE_URL`, `EMAIL_BACKEND` (`console` in dev), `OWNER_EMAIL`, `OWNER_PASSWORD`, `OWNER_NAME`.

`.env.example` lists all of them. `.env` is never committed.

## 11. Testing requirements

- Every AC ID above has at least one test. Every `/owner/*` endpoint has a `401` and a `403`
  (customer token) test. Every `/cart/*` endpoint has a `403` (owner token) test.
- Tests run against a dedicated PostgreSQL database, each test in a rolled-back transaction.
- Storage and email are replaced with in-memory fakes in tests.
