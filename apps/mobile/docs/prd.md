# PRD — Mobile (`apps/mobile`)

System PRD: `docs/prd.md` · API: `apps/api/docs/prd.md` · Stack: ADR 0002

Customer app built with Expo + Expo Router + NativeWind. Runs in Expo Go for the MVP.
UI copy in Bahasa Indonesia.

## 1. Screens

| Route (Expo Router) | Screen | Login required | Uses API |
|---|---|---|---|
| `(tabs)/index` | Katalog: product grid, search, category and brand chips | No | CAT-1, CAT-2, CAT-3 |
| `products/[slug]` | Product detail | No | CAT-4 |
| `(tabs)/cart` | Keranjang | Yes | CART-* |
| `(tabs)/account` | Akun: name, email, logout; or login/register buttons for guests | No | AUTH-5, AUTH-4 |
| `auth/login` | Login | No | AUTH-2 |
| `auth/register` | Register | No | AUTH-1 |
| `auth/forgot-password` | Request code, then code + new password | No | AUTH-6, AUTH-7 |

## 2. Acceptance criteria

### Catalog
- **M-CAT-1** Grid shows default image (placeholder if none), name, brand, formatted price,
  and "Stok habis" when `in_stock` is false.
- **M-CAT-2** Search input is debounced (400 ms) and sends `q`.
- **M-CAT-3** Category and brand chips filter the list; tapping an active chip clears it.
- **M-CAT-4** Infinite scroll, 20 items per page.
- **M-CAT-5** Pull to refresh.
- **M-CAT-6** Empty state "Produk tidak ditemukan"; error state with a retry button.

### Product detail
- **M-PRD-1** Swipeable image gallery in `position` order, default image first shown.
- **M-PRD-2** Size selector (EU) and color selector built from variants. Combinations with
  stock 0 are shown disabled.
- **M-PRD-3** Quantity stepper limited to the selected variant's stock.
- **M-PRD-4** "Tambah ke keranjang" is disabled until a size and color are chosen.
- **M-PRD-5** A guest tapping it is sent to login, then returned to the same product.
- **M-PRD-6** `INSUFFICIENT_STOCK` and `PRODUCT_UNAVAILABLE` show specific messages.

### Cart
- **M-CART-1** List items with image, name, size, color, unit price, quantity stepper,
  line total, remove button.
- **M-CART-2** Unavailable items (`available: false`) are visually marked and excluded from subtotal.
- **M-CART-3** Subtotal from the API's `subtotal_idr`. The app never computes money itself.
- **M-CART-4** A disabled "Checkout (segera hadir)" button is shown. No checkout logic.
- **M-CART-5** Empty state with a button back to the catalog.

### Auth
- **M-AUTH-1** Register form: name, email, password (min 8), confirm password (client-side match).
  `EMAIL_ALREADY_REGISTERED` shown on the email field.
- **M-AUTH-2** Successful register or login stores tokens in `expo-secure-store` and goes back
  to the previous screen (or the catalog).
- **M-AUTH-3** An owner account logging in on mobile sees "Akun ini khusus dashboard" and is logged out.
- **M-AUTH-4** Expired access token is refreshed once automatically; failure logs the user out.
- **M-AUTH-5** Forgot password: same two-step flow and messages as the dashboard (D-AUTH-7).
- **M-AUTH-6** Logout from the account tab revokes the refresh token and clears secure storage.

### General
- **M-GEN-1** API base URL comes from `EXPO_PUBLIC_API_URL`.
- **M-GEN-2** Server state uses TanStack Query; cart mutations invalidate the cart query.
- **M-GEN-3** All API calls go through `@ginantaka/api-client`.

## 3. Out of scope
Checkout, order history, wishlist, profile editing, push notifications, dark mode,
App Store / Play Store builds (roadmap item).

## 4. Testing
- Jest + @testing-library/react-native.
- Component tests for: product card (price format, out-of-stock label), variant selector
  (disabled combinations, add button state), cart item (unavailable state), register form validation.
- Unit tests for the auth refresh logic and error-code → message mapping.
- `tsc --noEmit` must pass.
