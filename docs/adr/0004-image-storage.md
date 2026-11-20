# ADR 0004 — Image storage on Cloudflare R2 with presigned uploads

**Status:** Accepted · **Date:** 2026-10-06

## Context
Products have up to 5 photos; brands have an optional logo. Images must be served fast to
the mobile app and cost nothing at portfolio scale.

## Decision
- **Cloudflare R2** (S3-compatible), one bucket per environment (`*-dev`, `*-prod`).
  The free tier (10 GB storage, free egress) covers the MVP.
- **Upload flow (direct to R2, not through the API):**
  1. Client asks the API for a presigned PUT URL, sending `content_type` and `size_bytes`.
  2. API validates and returns `{upload_url, object_key, expires_in}` (5 minutes).
  3. Client uploads the file to R2 with that URL.
  4. Client calls the API with `object_key` to attach the image. The API checks the object
     exists (HEAD) and that the key prefix belongs to that product or brand.
- **Allowed types:** `image/jpeg`, `image/png`, `image/webp`.
  SVG is rejected because it can carry scripts.
- **Max size:** 5 MB per product image, 2 MB per brand logo.
- **Keys:** `products/{product_id}/{uuid}.{ext}`, `brands/{brand_id}/{uuid}.{ext}`.
- The database stores keys only. Public URLs are built from `PUBLIC_ASSET_BASE_URL`.
- Deleting an image or replacing a logo deletes the R2 object after the database commit.
  A failed object delete is logged, not raised (orphans are acceptable in the MVP).
- **Tests** use an in-memory fake that implements the same `StorageService` interface.
  No test talks to R2.
- **Local development** uses the real `*-dev` R2 bucket.

## Alternatives considered
- **Upload through FastAPI.** Simpler client, but large bodies through the API cost memory
  and do not fit serverless limits.
- **MinIO locally.** Rejected to avoid another container to maintain; the dev bucket is free.
- **Cloudinary / Cloudflare Images.** Better resizing, but paid beyond small quotas.
  No image resizing in the MVP; clients limit display size.

## Consequences
- The dashboard needs R2 CORS configured to allow PUT from its origins.
- Orphaned objects can appear if a client uploads but never attaches. Cleanup job is post-MVP.
