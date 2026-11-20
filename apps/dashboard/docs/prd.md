# PRD — Dashboard (`apps/dashboard`)

System PRD: `docs/prd.md` · API: `apps/api/docs/prd.md` · Stack: ADR 0002

Owner-only web app for managing the catalog. SvelteKit SPA (`adapter-static`, `ssr = false`).
UI copy in Bahasa Indonesia. Components from shadcn-svelte.

## 1. Routes

| Route | Screen | Uses API |
|---|---|---|
| `/login` | Login | AUTH-2 |
| `/forgot-password` | Request code, then enter code + new password | AUTH-6, AUTH-7 |
| `/` | Redirects to `/products` | — |
| `/products` | Product list | OPRD-1 |
| `/products/new` | Create product | OPRD-2 |
| `/products/[id]` | Edit product, variants, images | OPRD-3/4/5, OVAR-*, OIMG-* |
| `/categories` | Category list with inline create/edit/delete | OCAT-* |
| `/brands` | Brand list with create/edit/delete and logo | OBRD-* |

All routes except `/login` and `/forgot-password` require a logged-in owner.

## 2. Acceptance criteria

### Auth
- **D-AUTH-1** Login with owner credentials stores tokens (ADR 0003) and redirects to `/products`.
- **D-AUTH-2** Login with a customer account shows "Akun ini tidak punya akses dashboard",
  calls logout, and stays on `/login`.
- **D-AUTH-3** `INVALID_CREDENTIALS` shows "Email atau password salah".
- **D-AUTH-4** Visiting a protected route without a session redirects to `/login`.
- **D-AUTH-5** A `401` from any request triggers one refresh attempt; if it fails, the session
  is cleared and the user goes to `/login`.
- **D-AUTH-6** Logout revokes the refresh token and returns to `/login`.
- **D-AUTH-7** Forgot password: step 1 email → always shows "Jika email terdaftar, kode sudah dikirim";
  step 2 code + new password → success message and link to `/login`. Each reset error code has its
  own message.

### Products
- **D-PRD-1** List shows name, default image thumbnail, brand, category, price (formatted Rupiah),
  total stock, active badge. Search, category, brand, and active filters update the URL query.
- **D-PRD-2** Pagination of 20 per page.
- **D-PRD-3** Create form: name, description, price (integer input, no decimals), category, brand,
  active toggle (default off). On success, go to `/products/[id]`.
- **D-PRD-4** Edit page has three sections: details, variants, images.
- **D-PRD-5** Delete asks for confirmation, then returns to `/products`.

### Variants (on product page)
- **D-VAR-1** Table of size, color, SKU, stock with inline edit.
- **D-VAR-2** Add row form. `VARIANT_EXISTS` and `SKU_TAKEN` show field-level errors.
- **D-VAR-3** Delete with confirmation.

### Images (on product page)
- **D-IMG-1** Upload accepts jpeg/png/webp up to 5 MB, validated on the client before requesting
  an upload URL. Flow per ADR 0004.
- **D-IMG-2** Upload control is disabled with "Maksimal 5 foto" when the product has 5 images.
- **D-IMG-3** Default image has a visible badge. "Jadikan utama" sets another image as default.
- **D-IMG-4** Images can be reordered (drag and drop or up/down buttons); order is saved with OIMG-4.
- **D-IMG-5** Delete with confirmation. After deleting the default, the UI shows the new default
  returned by the API.

### Categories and brands
- **D-CAT-1** List with product count. Create and rename inline. `CATEGORY_NAME_TAKEN` shown on the field.
- **D-CAT-2** Delete blocked with the message from `CATEGORY_IN_USE` ("Kategori masih dipakai produk").
- **D-BRD-1** Same as D-CAT-1/2 for brands, plus logo thumbnail.
- **D-BRD-2** Logo upload (jpeg/png/webp, ≤ 2 MB), replace, and remove.

### General
- **D-GEN-1** Every mutation shows a success toast or an error message mapped from the error `code`.
- **D-GEN-2** Money is always displayed with `formatRupiah` (e.g. `Rp 1.250.000`).
- **D-GEN-3** All API calls go through `@ginantaka/api-client`. No hand-written API types.

## 3. Out of scope
Dashboard home/analytics, customer list, owner profile editing, password change while logged in,
bulk import, dark mode toggle.

## 4. Testing
- Vitest unit tests for helpers (formatting, error-code → message mapping, auth refresh logic).
- `load` functions tested with a mocked `fetch`.
- Component tests for: login form, product form validation, image manager (limit, default badge).
- `svelte-check` must pass.
