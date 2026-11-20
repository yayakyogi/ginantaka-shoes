# Data Model — MVP

PostgreSQL. All tables have `id` (`uuid`, UUIDv4, primary key, default `gen_random_uuid()`) unless noted.
Foreign keys are `uuid` too. See ADR 0007.
All timestamps are `timestamptz` in UTC. `created_at` / `updated_at` exist on every
table and are omitted below for brevity.

Changes to this file require an Alembic migration in the same change.

## users

| Column | Type | Rules |
|---|---|---|
| email | text | Unique, stored lowercase and trimmed |
| password_hash | text | Never returned by any endpoint |
| name | text | Required, 1–100 chars |
| role | text | `owner` or `customer` (check constraint) |

## refresh_tokens

| Column | Type | Rules |
|---|---|---|
| user_id | FK → users | On delete cascade |
| token_hash | text | Unique. Only the hash is stored |
| expires_at | timestamptz | 30 days after issue |
| revoked_at | timestamptz, nullable | Set on logout, rotation, or password reset |

## password_resets

| Column | Type | Rules |
|---|---|---|
| user_id | FK → users | On delete cascade |
| code_hash | text | HMAC-SHA256 of the 6-digit code, keyed with `JWT_SECRET` |
| expires_at | timestamptz | 15 minutes after issue |
| attempts | int | Starts at 0, max 5 |
| used_at | timestamptz, nullable | Set on successful reset |

Requesting a new code invalidates (sets `used_at` on) any unused code for the same user.

## categories

| Column | Type | Rules |
|---|---|---|
| name | text | Unique (case-insensitive), 1–50 chars |
| slug | text | Unique, generated from name |

## brands

| Column | Type | Rules |
|---|---|---|
| name | text | Unique (case-insensitive), 1–50 chars |
| slug | text | Unique, generated from name |
| logo_key | text, nullable | R2 object key, prefix `brands/{brand_id}/` |

## products

| Column | Type | Rules |
|---|---|---|
| name | text | 1–150 chars |
| slug | text | Unique, generated from name, suffixed `-2`, `-3`… on collision |
| description | text | Optional, max 5,000 chars |
| price_idr | int | > 0 |
| category_id | FK → categories | Required. On delete restrict |
| brand_id | FK → brands | Required. On delete restrict |
| is_active | bool | Default `false`. Only active products are visible to the public |

## product_variants

| Column | Type | Rules |
|---|---|---|
| product_id | FK → products | On delete cascade |
| size_eu | int | 30–50 |
| color | text | 1–30 chars |
| sku | text | Unique across all variants |
| stock | int | >= 0 |

Unique constraint: `(product_id, size_eu, color)`.

## product_images

| Column | Type | Rules |
|---|---|---|
| product_id | FK → products | On delete cascade |
| object_key | text | R2 object key, prefix `products/{product_id}/` |
| position | int | Gallery order, 0-based, contiguous per product |
| is_default | bool | Exactly one default per product when the product has images |

```sql
CREATE UNIQUE INDEX uq_product_images_one_default
  ON product_images (product_id)
  WHERE is_default;
```

Rules:
1. Max 5 images per product.
2. The first image saved for a product becomes default automatically.
3. Setting a new default unsets the old one in the same transaction.
4. Deleting the default image promotes the remaining image with the lowest `position`.
5. Deleting any image re-numbers `position` to stay contiguous.

## carts

| Column | Type | Rules |
|---|---|---|
| user_id | FK → users | Unique (one cart per customer). On delete cascade |

Created lazily on the first cart request.

## cart_items

| Column | Type | Rules |
|---|---|---|
| cart_id | FK → carts | On delete cascade |
| variant_id | FK → product_variants | On delete cascade |
| quantity | int | >= 1 |

Unique constraint: `(cart_id, variant_id)`. Adding an existing variant increases quantity.

## Relationships

```
users 1─1 carts 1─* cart_items *─1 product_variants *─1 products
users 1─* refresh_tokens
users 1─* password_resets
categories 1─* products *─1 brands
products 1─* product_images
```

## Why object keys, not URLs

Storing `object_key` instead of a full URL means the public asset domain can change
(r2.dev during development, a custom domain later) without a data migration. The API
builds URLs as `{PUBLIC_ASSET_BASE_URL}/{object_key}`.
