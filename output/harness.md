# Campus Customs — Project Harness

## Problem 2 — Database tables and fields

Inspected `data/campus_customs.db` on September 30, 2026 using SQLite in read-only mode. The database was not changed. Counts below describe this inspection, not live stock guarantees.

### `catalogue` — 102 products

| Field | SQLite type / constraints | Why it matters for the shop or chatbot |
| --- | --- | --- |
| `product_id` | TEXT, primary key | Identifies a product and connects its catalogue entry to size-specific inventory. |
| `name` | TEXT, NOT NULL | Supplies the product title shown in cards and chat recommendations. |
| `garment_type` | TEXT, NOT NULL | Supports category filtering and requests such as “show me hoodies.” |
| `description` | TEXT, NOT NULL | Provides recorded product details for matching and grounded answers. |
| `colors` | TEXT, NOT NULL; JSON list | Supports color preferences; decode the JSON before returning colors to the frontend. |
| `search_tags` | TEXT, NOT NULL; JSON list | Supplies search terms for themes, teams, events, and designs. |
| `image_file_path` | TEXT, NOT NULL | Locates the product photo to display beside search results and recommendations. |
| `price` | REAL, NOT NULL | Supplies the recorded price for product cards, budget filters, and chat answers. |

All 102 `colors` and `search_tags` values parse as JSON lists. Recorded prices range from 32.00 to 98.00; there is no currency column, so currency is an application decision to confirm later. Format prices to two decimal places for display; SQLite REAL is floating-point storage.

Image paths look like `products/2025-yale-vs-harvard-t-shirt.jpg` and resolve relative to `data/`, not the homework folder. All 102 referenced images exist there. The backend will need to map these files to browser-accessible URLs.

### `inventory` — 612 product/size entries

| Field | SQLite type / constraints | Why it matters for the shop or chatbot |
| --- | --- | --- |
| `id` | INTEGER, primary key, AUTOINCREMENT | Identifies an inventory row for precise stock updates. |
| `product_id` | TEXT, NOT NULL; foreign key to `catalogue.product_id` | Connects a stock count to its product name, image, and price. |
| `size` | TEXT, NOT NULL | Identifies the size whose availability the shopper is asking about. |
| `quantity` | INTEGER, NOT NULL | Gives the recorded available count for that product and size. |

The pair `(product_id, size)` is UNIQUE. Every product currently has entries for XS, S, M, L, XL, and XXL. Quantities range from 0 to 25; 145 entries have zero stock, and none are negative. A product match does not imply that the requested size is available: query its size row before answering. If a row is missing in the future, report availability as unknown rather than inventing a count.

### `users` — 3 accounts

| Field | SQLite type / constraints | Why it matters for the shop or chatbot |
| --- | --- | --- |
| `id` | INTEGER, primary key, AUTOINCREMENT | Identifies an account and links it to its saved chat messages. |
| `name` | TEXT, NOT NULL | Supplies the account's display name and must be populated during signup. |
| `email` | TEXT, NOT NULL, UNIQUE | Identifies an account for login and prevents duplicate stored email values. |
| `password_hash` | TEXT, NOT NULL | Supports backend password verification; never return it to the browser or send it to the agent. |
| `created_at` | TEXT, NOT NULL; defaults to `datetime('now')` | Records account creation time; SQLite's default uses UTC. |
| `first_name` | TEXT, nullable | Allows a personalized greeting when available. |
| `last_name` | TEXT, nullable | Supports a separate surname field in account details. |

Both optional name fields are populated for the existing accounts, but new code must handle NULL. Signup must still fill the required `name` field. The schema does not specify the password-hashing algorithm; authentication compatibility will need verification during implementation. No account values or password hashes are reproduced here.

### `chat_messages` — 22 saved messages

| Field | SQLite type / constraints | Why it matters for the shop or chatbot |
| --- | --- | --- |
| `id` | INTEGER, primary key, AUTOINCREMENT | Identifies a saved message and provides a stable ordering tie-breaker. |
| `user_id` | INTEGER, NOT NULL; foreign key to `users.id` | Associates history with its owner; history queries must use the authenticated user's ID. |
| `role` | TEXT, NOT NULL | Distinguishes shopper messages from assistant replies when rebuilding the conversation. |
| `content` | TEXT, NOT NULL | Stores the message text displayed in chat history. |
| `products_json` | TEXT, nullable | Stores a JSON payload associated with product recommendations for redisplay alongside a reply. |
| `created_at` | TEXT, NOT NULL; defaults to `datetime('now')` | Records message time for chronological history. |

There are 11 `user` and 11 `assistant` messages. `products_json` is NULL in 11 rows and parses as a JSON list in the other 11; its element structure must be checked when defining the response models. Saved recommendations are historical: re-query current price and stock before making a new availability claim. There is no conversation/session ID, so separate chat threads are not represented by this schema. Private message contents are not reproduced here.

### `sqlite_sequence` — 3 internal bookkeeping rows

| Field | SQLite type / constraints | Why it matters for the shop or chatbot |
| --- | --- | --- |
| `name` | No declared type | Names a table using AUTOINCREMENT; SQLite maintains this internally. |
| `seq` | No declared type | Tracks that table's last AUTOINCREMENT sequence value; let SQLite manage IDs. |

This is a SQLite system table, not shop content or an agent tool input.

### Relationships and implementation notes

- `catalogue.product_id` → `inventory.product_id`: one product has many size entries; join these tables for price-and-stock answers.
- `users.id` → `chat_messages.user_id`: one account has many messages; access must be scoped to the authenticated account.
- Both foreign keys use `NO ACTION` for update/delete, with no cascading deletion. Enable `PRAGMA foreign_keys = ON` on each backend connection to enforce them.
- `PRAGMA foreign_key_check` found no violations; `PRAGMA quick_check` returned `ok`.
- The schema has no CHECK constraints for nonnegative prices/quantities, allowed message roles, or valid JSON. Validate these when implementing writes and models.
- There are no orders, carts, payments, or separate color-variant inventory tables. Current stock is distinguished only by product and size.
- Keep the database and product images out of the public repository, as required for this assignment.

Later problems will extend this file with implemented models, tools, safety rules, and operating specifications.

## Problem 3 — Storefront and catalogue API

### Website

`frontend/` uses React, Vite, TypeScript, and React Router. The design combines Yale navy (`#00356b`), warm cream, soft blue, serif headings, and a bulldog drawn in HTML/CSS. Layouts adapt to desktop and mobile, with visible keyboard focus, labeled inputs, a skip link, and an Enter-to-send chat form.

| Route | Shopper experience |
| --- | --- |
| `/` | Original welcome copy, featured products from the database, and links to the collection and shop story. |
| `/products` | All catalogue images, names, prices, and short descriptions; search, garment-type filtering, and name/price sorting. |
| `/products/:id` | Large product photo, full description, price, colors, selectable sizes, and recorded stock, including sold-out sizes. |
| `/about` | Original community-focused copy and the real shop's address/link. |
| `/login`, `/create-account` | Labeled account previews with disabled forms; no account creation or authentication yet. |

Public context was read from [Yale Bulldog Blue by Campus Customs](https://yalebulldogblue.com) on September 30, 2026: Yale apparel and community collections, New Haven location at 57 Broadway, and default USD pricing. Home/About prose was written for this project; product descriptions, images, stock, and prices come from the local catalogue, not scraped prices. The student-project status is shown in the footer and About page. Google Fonts supply DM Sans and Libre Caslon Display, with local fallbacks if unavailable.

### Backend and typed responses

`backend/main.py` opens SQLite with `mode=ro`, uses parameterized product-ID queries, and closes connections after reads. A read transaction keeps product and inventory results consistent within each response. Only the `data/products/` directory is mounted for image serving; the database and account tables are not exposed.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/products` | Returns the catalogue with parsed color/tag lists and size-stock entries. |
| `GET /api/products/{product_id}` | Returns one product, or HTTP 404 if it does not exist. |
| `GET /api/images/{path}` | Serves an original product photo using the catalogue's path relative to `data/products/`. |

The `Stock` Pydantic model contains `size` and `quantity` so availability stays size-specific. `Product` contains `product_id`, `name`, `garment_type`, `description`, `colors`, `search_tags`, `image_url`, `price`, and `inventory`: the frontend receives the fields needed for browsing and matching, a browser-ready image URL, and typed stock entries. These models currently live in `backend/main.py`; future problems can extend or move them into shared model files.

### Chat boundary and current limits

- The floating bulldog panel is available on every route. Opening it focuses the message input; Escape closes it and returns focus to the launcher.
- `sendChatMessage` in `frontend/src/api.ts` is the adapter to replace with a backend agent call later. It currently returns an explicit preview message, with no price/stock advice, external request, or AI usage.
- Messages stay in page memory only and are discarded on reload. The input allows up to 1,000 characters and blocks empty sends.
- The catalogue loads once per app mount, with retry on failure. Search/filter/sort runs locally over all 102 products; pagination is not needed for this dataset. Detail pages use this loaded catalogue; the individual-product endpoint is also ready for later use.
- Stock is a snapshot from page load, not a reservation. Missing stock is treated as unavailable information, and zero stock is shown as sold out. Refresh the page for new database values.
- Currency is displayed as USD based on the source shop, since the database itself has no currency field.
- Account creation, authentication, checkout, database writes, and agent integration are future work. No API key is needed for this problem.
- Vite proxies `/api` to FastAPI during development and local production preview. A public deployment will need explicit hosting/proxy configuration.
- `.gitignore` excludes the local database, source product images, secrets, and generated dependencies/build files; only screenshots under `output/screenshots/` are exempted as evidence.

### Running and verification

See `README.md` for installation and two-terminal startup instructions. FastAPI runs on `127.0.0.1:8000` without a reloader; Vite runs on `127.0.0.1:5173` with strict port selection.

The production check is `npm run build` in `frontend/`. Browser/API checks are in `frontend/tests/storefront.spec.ts`, run with `npx playwright test` while both servers are running. They cover all image URLs, product lookup, invalid IDs, database-path blocking, search/filter/sort, detail navigation and stock, mobile navigation/chat, disabled account previews, API failure/retry, and missing routes. Screenshot evidence is saved in `output/screenshots/`.

Verified September 30, 2026: TypeScript and Vite production build passed; all five Playwright tests passed. Desktop (1440px) and mobile (390px) screenshots were reviewed. The API successfully served all 102 catalogue images. No database writes or model calls were made.

- [Desktop home](screenshots/p3-home-desktop.png)
- [Product listing](screenshots/p3-products-desktop.png)
- [Product detail with sold-out size](screenshots/p3-product-detail.png)
- [Mobile home](screenshots/p3-home-mobile.png)
- [Mobile chat preview](screenshots/p3-chat-mobile.png)

## Problem 4 — Accounts, login, and password protection

This section supersedes Problem 3's account-preview limitation. The website now supports signup, login, reload-persistent sessions, a private account page, and logout. The catalogue remains read-only, and the chat is still a local preview.

### User data and form behavior

Signup requires first name, last name, email, a password, and confirmation. Names are trimmed and limited to 80 characters each. Email is trimmed, validated with `EmailStr`, and normalized to lowercase. A unique index on `lower(trim(email))` prevents duplicate emails, including case variations. The existing required `name` column is filled from first and last name; `id` and `created_at` come from SQLite. Confirmation is checked but never stored.

New passwords must be 12–128 characters; passwords are not trimmed. Login accepts the shorter existing demo password for compatibility. Both browser and backend validate the form; client-side validation alone is not trusted. The UI provides show/hide controls, clear error messages, and disabled submit controls while a request is pending. Signup automatically signs in the new user. `/account` displays the authenticated user's public profile and logout; unauthenticated visitors are redirected to login.

The actual seeded test address is `test@campuscustoms.yale.edu`, correcting the typo in the assignment prompt. Its supplied password was verified against the existing hash, without resetting it.

### Password protection

- `users.password_hash` contains a salted scrypt hash generated by Werkzeug, using `N=32768`, `r=8`, `p=3`, and a random 16-character salt. The encoded value includes the algorithm parameters and salt, so a password can be verified without storing plaintext or a decryptable password.
- The seed uses `pbkdf2_sha256$salt$hex_digest` with 120,000 SHA-256 iterations. The backend verifies this legacy format with a constant-time digest comparison, then replaces it with scrypt only after a successful login. Other legacy accounts upgrade when their owners next sign in.
- Password request fields use Pydantic `SecretStr`. The validation-error handler returns a generic message rather than FastAPI's default response, which can echo invalid input. Application code does not log passwords, hashes, or session cookies.
- `PublicUser` deliberately contains only `id`, `name`, `first_name`, `last_name`, `email`, and `created_at`. No response returns password hashes or tokens in JSON. A dummy scrypt check for unknown accounts reduces login timing differences; nonexistent accounts and wrong passwords return the same message.
- Credentials go only to authentication endpoints. Future agent tools must not receive passwords, hashes, session tokens, or unrestricted access to users/session tables. The current chatbot makes no backend or model call.
- SQL values are parameterized, and database connections are closed after use. Static serving still exposes only product photos. The database and secrets stay out of Git.

Hashing reduces damage from a copied database, but cannot guarantee protection against a compromised server or make the publicly known demo password strong. Use HTTPS and change/remove demo credentials before public deployment.

### Sessions and the new `auth_sessions` table

The backend issues a cryptographically random 32-byte token on successful signup/login. Only its SHA-256 digest is stored, so a copied session-table value is not itself a usable browser token. Sessions last seven days, survive backend restarts, and are revoked by deleting their row. A successful login replaces the session previously attached to that browser. Expired rows are cleaned up on startup and session creation, and expired tokens are rejected even before cleanup.

| Field | SQLite type / constraints | Why it matters |
| --- | --- | --- |
| `token_hash` | TEXT, primary key, NOT NULL | Looks up a session without storing its raw cookie token. |
| `user_id` | INTEGER, NOT NULL; foreign key to `users.id`, ON DELETE CASCADE | Identifies the authenticated account; deleting an account removes its sessions. |
| `created_at` | INTEGER, NOT NULL | Records session creation as Unix seconds. |
| `expires_at` | INTEGER, NOT NULL; indexed | Enforces expiry and supports cleanup of old sessions. |

The browser receives `campus_session` as an HttpOnly, SameSite=Lax cookie scoped to `/api`, with no Domain attribute. JavaScript cannot read it, and the app does not use localStorage/sessionStorage for credentials. `/api/auth/me` restores the signed-in profile; account-page access is backed by server session checks, not only a frontend flag. Logout deletes the session and cookie. Switching accounts also resets the in-memory chat preview.

Local loopback development uses HTTP. Set `AUTH_COOKIE_SECURE=true` for HTTPS deployment, and set `AUTH_ALLOWED_ORIGINS` to exact trusted storefront origins. Cookie/session responses are marked `Cache-Control: no-store`; the API also sends `X-Content-Type-Options: nosniff`.

### Endpoints and limits

| Endpoint | Behavior |
| --- | --- |
| `POST /api/auth/register` | Validates the signup fields, inserts a user, creates a session, and returns the public profile (201). |
| `POST /api/auth/login` | Verifies the password, upgrades a legacy hash if needed, creates a session, and returns the public profile. |
| `GET /api/auth/me` | Returns the cookie-authenticated profile, or 401 if the session is absent, invalid, or expired. |
| `POST /api/auth/logout` | Revokes the current session, clears its cookie, and returns 204. |

Mutation endpoints require both a trusted `Origin` and `X-Requested-With: CampusCustoms`; no wildcard CORS policy is enabled. This supplements SameSite cookies against cross-site form submissions. The frontend and API share an origin through Vite's `/api` proxy. Defaults allow localhost/127.0.0.1 on ports 5173 and 4173.

Signup and login share a limit of 30 attempts per direct client IP per 10 minutes, including invalid submissions. The limiter is thread-safe but held in process memory; it resets on restart and needs shared storage/trusted proxy configuration before a multi-worker or proxied public deployment. Email ownership verification, password reset, MFA, and account deletion are not implemented. These limits are explicit; the project does not claim to be immune to human or AI-assisted attacks.

### Verification and evidence

Backend tests use temporary databases and check registration/hash storage, sanitized responses, HttpOnly cookies, session restoration/revocation, legacy hash upgrades, duplicate emails, mismatched/weak passwords, generic login errors, expired/forged tokens, origin enforcement, attempt limits, and the Secure-cookie setting. Browser tests use the supplied seed account and create one synthetic account in the real homework database, then verify reload, wrong-password handling, logout, and login again. The generated test password exists only in test memory.

Verified September 30, 2026: all six backend tests and all seven browser/API tests passed, and the TypeScript/Vite production build passed. A read-only follow-up inspection confirmed the new user's name fields and scrypt hash were saved, the seed hash upgraded to scrypt, both test sessions were revoked on logout, and SQLite integrity/foreign-key checks passed. Desktop login, mobile signup, and the signed-in account screenshots were reviewed.

- [Authentication verification results](auth-verification.json)
- [Desktop login](screenshots/p4-login-desktop.png)
- [Mobile signup](screenshots/p4-signup-mobile.png)
- [Signed-in account](screenshots/p4-account-desktop.png)

## Problem 5 — PydanticAI chatbot behind FastAPI

### Files and loading

`backend/main.py` is the Uvicorn entry point. From `backend/`, with the homework virtual environment activated, `uvicorn main:app --reload --port 8000` starts successfully. Package imports also support the older homework-folder command, `uvicorn backend.main:app --port 8000`. Paths derive from `__file__`, so changing the working directory does not break the database, image, prompt, or root `.env` paths.

| File | Responsibility |
| --- | --- |
| `backend/prompts/prompt.md` | Growing system prompt: warm Campus Customs voice, public New Haven shop context, grounded tool use, privacy and safety basics. |
| `backend/agent.py` | PydanticAI agent, Portkey client, structured output validation, conversation memory, and request/usage limits. |
| `backend/tools.py` | Read-only catalogue helper plus `search_products` and `get_product` agent tools. |
| `backend/models.py` | Shared product, stock, request, agent-result, API-reply, and history types. |
| `backend/main.py` | Authenticated chat routes alongside existing catalogue/account endpoints; client cleanup on shutdown. |

The agent is built lazily on the first chat request. `load_dotenv` reads `AI foundation/.env`, without overriding an already-set process environment value. `PORTKEY_API_KEY` configures an `AsyncOpenAI` client using `https://api.portkey.ai/v1`, `x-portkey-api-key`, and `x-portkey-provider: openai`. The exact requested course model is **`gpt-5.6 luna`**, passed through `OpenAIChatModel` and `OpenAIProvider`. The key is never placed in the frontend, prompt, response JSON, or logs.

The system prompt is read from the same `backend/prompts/prompt.md` when constructing the agent. Restart after editing only that Markdown file or the root `.env`, since the default Uvicorn reload watches Python files. Catalogue/account pages still work when the key is absent; chat returns a clear unavailable response. The official [OpenAI Python SDK documentation](https://developers.openai.com/api/docs/libraries) was consulted for client/environment guidance; the course gateway/model configuration follows this project's existing Portkey setup.

### Website → API → agent → product cards

1. A signed-in shopper types in the floating bulldog panel and presses Enter. `frontend/src/api.ts` sends `POST /api/chat` with `{ "message": "…" }`, the same-origin HttpOnly cookie, and `X-Requested-With: CampusCustoms`.
2. Vite forwards `/api` to FastAPI on port 8000. The server checks the cookie session and request origin, then validates `ChatRequest`. User IDs supplied in the body are forbidden; the backend obtains identity from authentication.
3. The agent receives the system prompt, the message, and recent user/assistant messages from this browser session. Its dependencies contain only the database path and an initially empty set of products retrieved during this run—not an account profile, cookie, or password.
4. The agent calls read-only catalogue tools and returns `AgentReply`. Output validation rejects product IDs not retrieved by tools during the current turn, allowing one correction attempt.
5. The server constructs `ChatReply` using the actual tool-returned product records. The widget displays the reply and linked cards; the page also shows a “Picked for you” collection. Prices, images, and size counts on these cards are database values, not model-authored fields.

Guests see a login link and cannot submit a model request. The UI shows a pending indicator, blocks duplicate sends, and retains the message for retry on failure. There is no offline/canned success fallback in the running app. The UI test suite explicitly stubs responses only inside Playwright tests.

| Type | Fields and reason |
| --- | --- |
| `Stock` | `size`, `quantity`: keeps availability specific to a size. |
| `ProductCard` | `product_id`, `name`, `garment_type`, `description`, `colors`, `search_tags`, `image_url`, `price`, `inventory`: shared catalogue/card data for tools and frontend. |
| `ChatRequest` | `message`: trimmed, 1–1,000 characters; extra fields forbidden. |
| `AgentReply` | `reply` (1–2,500 characters), `product_ids` (up to four): model prose plus verified references, without invented card metadata. |
| `ChatReply` | `reply`, `products`: browser-ready response with catalogue-backed cards. |
| `ChatMessage` | `role`, `content`, `products`: one visible conversation entry; no hidden reasoning or raw tool traces. |
| `ChatHistory` | `messages`: visible conversation entries returned for the authenticated browser session. |

`GET /api/chat/history` restores the current session's recent messages. Memory is scoped by a server-computed session fingerprint; clients cannot select another session/user. History keeps six successful turns, expires after 30 minutes without a successful turn, and is capped at 100 sessions with idle eviction. It survives page refreshes but not server restarts/reloads. The existing `chat_messages` table is deliberately not written in this problem; durable conversations can be added later.

### Initial tools and safety

`search_products(query, max_price, size, in_stock_only)` matches short keywords locally, normalizes common hoodie/shirt plurals, applies budget and size filters, and returns at most six matches ordered by price/name. It scans this small catalogue locally, without sending all 102 products to the model. `get_product(product_id)` returns one exact record with current size stock, or `None` when absent.

SQLite opens with `mode=ro`, queries are parameterized, and the tool connection's authorizer rejects reads of tables other than `catalogue` and `inventory`. There are no arbitrary SQL, shell, web-browsing, account, or write tools. The main shop endpoints reuse the same catalogue reader.

The prompt requires tools before specific product/price/stock claims and fresh lookups for follow-up stock questions. Zero stock is sold out, missing stock is unknown, and a match does not reserve an item. It distinguishes this student storefront from the commercial shop, avoids unsupported policy promises, and declines credential/other-user-data requests. Product text and user messages are untrusted content, not instructions to override the system prompt. No account profile or authentication secrets are sent to the model. Textual answers remain model-generated; live behavior must still be verified rather than assuming prompt instructions guarantee accuracy.

### Operating limits and errors

- Maximum four model requests and four tool calls per turn; one output/tool validation retry.
- Maximum 1,200 completion tokens per request, with a 20,000-token per-run usage limit enforced by PydanticAI (provider usage is checked as responses arrive).
- OpenAI client timeout: 25 seconds; SDK retries disabled. Overall agent turn timeout: 60 seconds; frontend abort timeout: 70 seconds.
- Maximum 15 attempted messages per account per 10 minutes; four concurrent agent turns per process and one active turn per browser session.
- HTTP 401 for missing/expired login, 403 for untrusted mutation origins, 422 for invalid input, 429 for rate/concurrency limits, and 503 for unavailable or unreliable model results.
- Failure details are sanitized; logs contain exception classes or aggregate request/tool/token counts, never credentials, cookies, shopper text, raw provider errors, or hidden reasoning. Successful visible messages alone enter conversation memory.
- Chat/profile responses use `Cache-Control: no-store`. Rate limits and memory are local to one backend process; production scaling requires shared state and the existing HTTPS/cookie configuration.

### Verification status

The TypeScript/Vite production build passed. All 12 backend tests passed, including a local PydanticAI `FunctionModel` that executes real catalogue tools, structured-card validation, unknown-ID rejection, history bounds/isolation, credential-table read blocking, and API authorization. Seven selected Playwright tests passed: existing catalogue/UI checks plus chat contract/cards and error recovery. These tests do not contact Portkey.

The backend-folder command `uvicorn main:app --reload --port 8000` was verified running. [The local chat UI screenshot](screenshots/p5-chat-local-interface.png) explicitly labels its mocked reply; [the mobile guest screenshot](screenshots/p5-chat-guest-mobile.png) shows the login requirement.

**Live verification passed:** after automatic approval review requested explicit authorization for the catalogue/inventory transfer, the user approved HW4 chatbot model calls. A direct real-agent run and one opt-in signed-in Playwright test both succeeded against `gpt-5.6 luna` through Portkey. The request was: “Show me up to two navy hoodies under $70 with size M in stock. Include exact prices and M quantities.”

Both replies named Ua Gameday Double Knit Hood at $45.00 with 8 in M, and Basic Hoodie Big Yale at $68.00 with 5 in M. These prices and quantities, and every returned card field, matched read-only SQLite checks. The direct run used two model requests, one `search_products` call, 3,528 input tokens, and 190 output tokens. This is one targeted shopping scenario, not a claim that all future answers will be correct.

The browser test additionally confirmed the signed-in UI/API/model path, visible recommendation cards, mobile layout, history restoration after page refresh, and rejection of history access after logout. Ordinary browser tests skip this live test; opt in with `RUN_LIVE_CHAT=1 npx playwright test tests/chat-live.spec.ts` to incur model calls intentionally.

- [Direct real-agent reply](p5-agent-response.json)
- [Real browser chat response and checks](p5-live-chat.json)
- [Live desktop chat](screenshots/p5-chat-live-desktop.png)
- [Live mobile chat](screenshots/p5-chat-live-mobile.png)
- [Verification summary](p5-verification.json)

## Problem 6 — Product information and stock tools

The agent now has three registered tools. The initial P5 `get_product` tool has been replaced by two explicit lookups, so price/description and size-stock questions have clear contracts. Existing product pages and chat cards keep their `ProductCard` format.

| Tool | Arguments | Return type and purpose |
| --- | --- | --- |
| `search_products` | `query`, optional `max_price`, optional `size`, `in_stock_only` | Up to six `ProductCard` objects, cheapest first; finds IDs and filters browsing recommendations using real catalogue/inventory values. |
| `get_product_info` | Exact `product_id` | `ProductInfoResult`; reads a product's actual description, price, type, and colors, or explicitly reports a missing product. |
| `get_stock` | Exact `product_id`, optional `size` | `StockLookupResult`; reports the requested size's quantity/status, or all recorded sizes and their total when no size is supplied. |

All three read `data/campus_customs.db` in read-only mode. SQL parameters are bound rather than interpolated, and the connection authorizer permits reads only from `catalogue` and `inventory`. The agent has no database-write tool. Lookups reread SQLite every time; the per-run `seen_products` map hydrates cards but is never used as a source of cached prices/stock. Descriptions and prices come from `catalogue`; quantities come from `inventory`, linked by `product_id`.

### Lookup models and field choices

| Model / field | Why it matters |
| --- | --- |
| `ProductInfoResult.product_id` | Preserves the ID being looked up, including when it is missing. |
| `ProductInfoResult.found` | Explicitly distinguishes a successful lookup from a missing product. |
| `ProductInfoResult.product` | Holds `ProductInfo` when found; `null` when absent, so absence is never represented by a fake zero price. |
| `ProductInfo.product_id`, `name` | Tie the answer to the exact catalogue item and its display name. |
| `ProductInfo.description` | Supplies the recorded description without generating unsupported product attributes. |
| `ProductInfo.garment_type`, `colors` | Answer category and color questions with catalogue facts. |
| `ProductInfo.price` | Exact nonnegative finite price from SQLite. |
| `ProductInfo.currency` | Explicit `USD`, following the storefront convention; the database itself has no currency column. |
| `SizeStock.size` | Identifies which size a count belongs to. |
| `SizeStock.quantity` | Nonnegative count copied from the corresponding inventory row. |
| `SizeStock.status` | `in_stock` for positive counts, `out_of_stock` for zero; validated against quantity. |
| `StockLookupResult.product_id`, `product_name` | Identify the requested product; name is `null` when no product exists. |
| `StockLookupResult.requested_size` | Canonical requested size, or `null` for an all-size overview; keeps a size-specific answer separate from a total. |
| `StockLookupResult.status` | Distinguishes `in_stock`, `out_of_stock`, `size_not_found`, `product_not_found`, and `no_inventory`. |
| `StockLookupResult.quantity` | Requested-size count, or the sum across returned rows when no size was requested; `null` for unknown/missing information. |
| `StockLookupResult.sizes` | Matching `SizeStock` rows: one for a requested size, all recorded rows for an overview, and none for missing information. |

Model validators require found products to contain matching IDs; size statuses must agree with quantities; known totals must equal their returned size rows; and a requested-size result cannot contain a different size. Unknown states cannot contain numeric quantities or invented size rows. The shared `Stock` model now also rejects negative counts.

Size normalization accepts examples such as ` medium ` → `M`, `small` → `S`, `extra large` → `XL`, and `2XL` → `XXL`. Unknown labels are looked up rather than silently changed to another size. An empty explicit size prompts the agent to correct its tool arguments.

### Agent behavior

The same `backend/prompts/prompt.md` now requires `get_product_info` for specific price/description questions and `get_stock` for specific availability questions. Combined questions require both. If the product is unclear, the agent searches or asks for clarification; known IDs can be looked up directly. Follow-ups must use fresh tool calls rather than previous chat numbers. Multiple requested sizes may be looked up individually or reported from one all-size result, but each count must be attributed to its actual size.

- A recorded zero is explicitly “out of stock” or “sold out,” even if another size is available.
- An unlisted size is “not listed; availability cannot be confirmed.” It is not a known stock shortage.
- Missing inventory or a missing product yields unknown quantity (`null`), never an assumed zero.
- All-size totals must not be presented as the count in a particular size; no restock dates or prices are invented.

A live check caught a reply saying an unlisted size was “not available.” The prompt now explicitly forbids that inference. If all stock lookups return unknown quantities, the output validator requires explicit uncertainty (“availability cannot be confirmed,” for example) and requests a correction for claims such as “sold out,” “out of stock,” “not available,” “not offered,” “unavailable,” or “0 available.” If correction fails, the request fails safely rather than serving that answer. This is a targeted English-language check, not a guarantee against every possible inaccurate wording.

The existing current-turn product-ID validation remains in place: cards must come from products actually retrieved during that turn. The model-request limit is now five, allowing up to four sequential tool calls plus a final answer; the four-tool-call, token, timeout, and rate limits remain in place.

### Verification

Local tests cover actual lookup fields, price/stock changes between calls, aliases, an in-stock size, a zero-stock size, an unlisted size, an unknown product, empty inventory, total quantities, SQL injection strings, and model-level consistency checks. Mutations happen only in a temporary test database. A local PydanticAI test exercises both dedicated tools, and another verifies that an incorrect “unavailable” answer for missing stock is rejected.

The opt-in `python -m backend.tests.verify_p6` run uses the approved Portkey model and saves questions, visible replies, invoked tool names, typed lookup results, and token counts to [p6-lookup-verification.json](p6-lookup-verification.json). It reads the supplied database without changing it.

Verified September 30, 2026: all 18 backend tests passed. The saved live sequence confirms `get_product_info` returned the actual Ua Gameday Double Knit Hood description and $45.00 price, and `get_stock` returned M = 8 (`in_stock`), L = 0 (`out_of_stock`), and 3XL = `null` (`size_not_found`). After the wording correction, the live reply explicitly said that 3XL is not listed and its availability cannot be confirmed. The final unknown-size check reused the already-verified price and M/L conversation context with `--resume-last`, avoiding repeated model calls for those successful cases.

## Problem 7 — Handsome Dan’s search results reach the page

The assistant is now **Handsome Dan** in the system prompt, PydanticAI agent name (`handsome_dan`), launcher, chat header, welcome text, loading text, and accessible input label. The Yale navy/cream results shelf includes the existing HTML/CSS bulldog.

### Search flow

1. The signed-in shopper sends a message through the chat widget to `POST /api/chat`.
2. The same `backend/prompts/prompt.md` tells the agent to call `search_products` immediately for a broad category question, such as “what hoodies do you have?”, without requiring a budget or size first.
3. The tool reads `catalogue` and `inventory` from SQLite, normalizes category/size aliases, applies the requested filters, and sorts by price then name. It counts all matches locally but returns at most six full `ProductCard` records.
4. The tool saves its `ProductSearchResult` in the current run's `ShopDependencies.last_search`. After a successful agent answer, `ShopChat` copies that exact result into `ChatReply.search`; the model does not author the card fields or match count. If several searches run in one turn, the last search supplies the shelf.
5. FastAPI serializes the typed reply. React renders `search.products` using the same `ProductCard` component as the collection, with image, name, exact USD price, and a description clamped to two lines. The shelf shows active filters and “Showing N of M matches.” Up to four separately selected, verified `ChatReply.products` appear as compact links inside chat.
6. Clicking any page card opens `/products/:id`, the existing P3 route with a large image, full description, price, colors, and size stock. The search shelf is hidden on detail routes so the full item appears first, and browser Back restores the shelf. The chat also offers a link to view the finds on the products page.

### Search model fields

| Field | Why it matters |
| --- | --- |
| `ProductSearchResult.query` | Actual short keywords used by the tool, displayed as a search label. |
| `max_price` | Optional inclusive USD budget; shown to make the applied price constraint clear. |
| `size` | Optional normalized size, so a filter such as “medium” is displayed as `M`. |
| `in_stock_only` | Records whether positive stock was required in the requested size, or any size if none was specified. |
| `total_matches` | Exact number of matching database records before the six-card limit; avoids presenting a selection as the entire catalogue. |
| `products` | Up to six database-backed `ProductCard` objects, with stable IDs, image URLs, name, price, description, and inventory. Stable IDs preserve detail navigation. |
| `ChatReply.search` / `ChatMessage.search` | Nullable search result shared by the live reply and saved history. `null` means no search happened; a result with zero matches means the search found nothing. |

The P6 `search_products` return type is now this wrapper instead of a bare card list. The two dedicated lookup tools and their stock semantics remain as documented in P6. The frontend mirrors the contract in `src/api.ts`.

### Page and history behavior

A new search replaces the previous shelf, including a zero-match search, which shows “No matches this time, bulldog” and clears stale cards. A non-search reply with specific product cards shows those picks; a greeting or thanks with no cards preserves existing results. “Hide picks” dismisses the shelf in the current page state. Opening chat after refresh restores the latest meaningful result from the session's retained history, even when a later reply was just thanks. A zero-match search is itself meaningful and restores the empty state. Logging out clears the displayed picks. History remains bounded and in memory, as in P5; a backend restart or history expiry removes it. Displayed results are snapshots, and a new search rereads the database.

All matching is local keyword/alias matching over the small catalogue, not semantic/vector search or pagination. At most six matches are displayed; the normal collection remains available to browse further. Product text is rendered as React text, not executable HTML. No database or source product images are added to the submission.

### Verification

20 backend tests passed, including exact counts with more than six matches, database prices, normalized filters, zero matches versus no search, and serialized search history. Eight local browser tests passed, including search replacement, thanks preserving picks, reload restoration, zero results clearing cards, page-card navigation, full detail text/image and size stock, and the existing compact chat-card links. The production TypeScript/Vite build passed. Local browser chat responses are explicitly mocked; the separate opt-in live test uses the approved model connection.

Live verification passed September 30, 2026 with the approved `gpt-5.6 luna` Portkey connection. “What hoodies do you have, Handsome Dan?” returned `query="hoodies"`, 27 total matches, and six displayed cards. Every returned card equaled its catalogue API record. Clicking the Ua Gameday Double Knit Hood page card opened the full detail view with its database description, $45.00 price, and recorded size stock. Desktop/mobile layout, Back navigation, and restoration after refresh passed.

- [Live structured response and checks](p7-search-verification.json)
- [Desktop search](screenshots/p7-search-live-desktop.png)
- [Mobile search](screenshots/p7-search-live-mobile.png)
- [Detail opened from a search card](screenshots/p7-search-product-detail.png)

Rerun intentionally with both servers running: from `frontend/`, `RUN_LIVE_CHAT=1 npx playwright test tests/search-live.spec.ts`. This makes a real model request; ordinary test runs skip it. The verification signs in with the supplied test account and logs out afterward; it changes only authentication sessions, not catalogue or inventory records.

## Problem 8 — Customer memory, guests, and current-page context

This section supersedes P5–P7's session-only history and sign-in requirement. Signed-in conversations now persist by account, guests can chat temporarily, and each model run receives limited customer and page context.

### Database storage and account isolation

The existing `chat_messages` table already contained 22 rows. `backend/history.py` preserves those rows and adds two nullable columns through an idempotent startup migration. The model cannot call the storage functions: FastAPI and `ShopChat` perform persistence separately from the read-only catalogue tools.

| Column | Purpose |
| --- | --- |
| `id` | Increasing primary key; deterministic message order even when timestamps are equal. |
| `user_id` | Foreign key to `users.id`; derived exclusively from the validated login cookie, never from the request body. |
| `role` | `user` or `assistant`, used to reconstruct the conversation. |
| `content` | The shopper's submitted message or the verified assistant reply. |
| `products_json` | Product-card snapshots for restoring compact links and item recommendations. |
| `created_at` | Existing SQLite UTC timestamp, defaulting to `datetime('now')`. |
| `search_json` (new) | Nullable serialized `ProductSearchResult`; preserves search filters, counts, cards, and zero-match results. |
| `page_context_json` (new) | The user message's page type and product ID at send time, allowing older references to be interpreted correctly. |

An index on `(user_id, id)` supports account-history reads. After a successful agent response, the user message and assistant message are inserted together in one transaction with bound SQL parameters. A failed model run or database save does not leave half a conversation pair. The save finishes before the API reports success. This stores ordinary conversation text and product metadata, not raw model traces, system prompts, account profiles, or authentication tokens. If a shopper explicitly asks for their own email and the assistant replies with it, that reply is naturally part of the saved conversation.

`GET /api/chat/history` derives the account from the session and loads its latest 100 messages in chronological order. All saved rows remain in SQLite; this initial UI has no older-history pagination or deletion controls. Each agent run rereads that account's history and uses the latest six turns (12 messages), keeping model context bounded. Older preferences outside that window are not guaranteed to be remembered. Returning after logout, a fresh login/browser, or a backend restart restores the saved account messages. Existing malformed legacy product metadata is omitted without discarding the message text. Stored product cards are historical snapshots; fresh factual answers still require catalogue tools.

Requests cannot supply a `user_id`, profile, or email override: extra body fields are rejected. A query such as `/api/chat/history?user_id=another-user` does not alter the account chosen by the session. An invalid or expired login cookie returns 401 rather than silently creating a guest turn. Authenticated accounts have a shared per-account busy guard across sessions in the current backend process. Login/logout remount the widget, clear old picks, and reload the appropriate history; late responses from an aborted widget cannot restore the previous account's picks. Guest and account histories are never merged.

### Guest memory

Guests receive an opaque random `campus_guest` HttpOnly, SameSite=Lax cookie scoped to `/api`. Its SHA-256 digest identifies a temporary server-memory conversation. The cookie has no account identity, and neither it nor its digest goes to the model. `AUTH_COOKIE_SECURE` controls HTTPS cookie handling as for login cookies.

Guest turns use the existing six-turn window, 30-minute inactivity expiry, and bounded memory map. They can survive an ordinary refresh while the cookie and process remain alive, but disappear after expiry, eviction, or server restart. No guest messages are inserted into `chat_messages`. Guest rate limiting is per direct client IP (15 messages per 10 minutes), so obtaining a new guest cookie does not reset the limit. Signed-in rate limiting remains per account. The UI explicitly labels guest conversations temporary and offers login to save future chats.

### Customer fields seen by the agent

FastAPI constructs a `CustomerContext` from the authenticated `PublicUser` and places it in `ShopDependencies.customer`. A PydanticAI dynamic `@agent.instructions` function serializes that data for the current run; no general account lookup tool is exposed.

| Context field | Source and use |
| --- | --- |
| `customer.name` | Full name from the authenticated account, for recognizing the shopper. |
| `customer.first_name` | Optional first name for a natural greeting. |
| `customer.email` | Current account email, available when the shopper asks which account is signed in. The prompt discourages volunteering it. |
| `customer = null` | Guest run; no inferred or fabricated identity. |

The model does not receive user IDs, account creation dates, password inputs/hashes, login cookies, token digests, or other users' profiles through this context. The SQLite catalogue authorizer continues to deny reads of `users`, `auth_sessions`, and `chat_messages`. Profile values and stored messages are data, never instructions, and cannot change the authenticated identity. Operational logs record counts rather than shopper names, email, or chat text.

### Current page and “this item”

The frontend derives `PageContext` from `window.location.pathname` at send time, avoiding stale context during a React navigation transition; it sends neither a full URL/query string nor browser-authored product facts. For example:

```json
{
  "message": "Do you have this in pink?",
  "page_context": {
    "page": "product",
    "product_id": "ua-gameday-double-knit-hood"
  }
}
```

`page` is one of `home`, `products`, `product`, `about`, `account`, `login`, `create-account`, or `other`. Only a `product` page includes a product ID, and a product page requires it. Unknown extra context fields and malformed IDs are rejected; an ID absent from the catalogue returns 404 before a model call. FastAPI verifies the ID, and `ShopChat` resolves the current product from SQLite into `ShopDependencies.current_product`. The dynamic instructions contain the page type, product ID, and database name, while prices, colors, descriptions, and counts still require fresh tool calls.

The updated `backend/prompts/prompt.md` tells Handsome Dan to resolve “this/it” to that current item, prioritize a newly navigated page over previous item references, and honor explicitly named alternatives. On a non-product page it uses unambiguous recent context or asks for clarification. A pink question requires `get_product_info` for the current ID. Colors are listed per product and inventory is tracked per size, so the agent must not invent color-specific inventory or equate an unlisted color with sold-out stock. Prior user messages retain their original page IDs for historical context.

### Verification and limits

The backend tests use temporary databases and local PydanticAI `FunctionModel` responses, with no provider calls. They cover additive migration with legacy rows, new service/session restoration, independent accounts, guest isolation/non-persistence, atomic failure rollback, six-turn model context, account-wide concurrency guards, guest IP rate limits, exact customer context fields, current-page changes, forged identity/context rejection, and invalid login handling. The browser checks cover guest sending, route changes while chat stays mounted, login/logout history switching, and the existing search/detail behavior.

`frontend/tests/memory-live.spec.ts` passed using the real Portkey model after the user explicitly approved sending the signed-in shopper’s name and email. Automatic approval review had initially blocked those additional fields under the earlier catalogue-only approval; the follow-up “yes u may” resolved that block. The test verified current-item color answers, recalled preferences and account fields after a fresh login, database writes, and a guest turn that added no rows. Local UI screenshots remain separately labeled as local test responses.

Remaining development limits: history storage is not encrypted at rest; protect the local database as private account data. Multi-worker concurrency/rate limiting needs a shared implementation; the current Uvicorn development server uses one application process. A lost HTTP response after a successful commit can cause a retried message to be saved twice; idempotent client request IDs are not implemented yet. No database or source product images are included in Git.

Final local verification: 26 backend tests and all 10 selected browser scenarios passed; the two memory scenarios each passed three consecutive runs after the navigation timing fix. The production build passed. The real database migration preserved all 22 existing chat rows and 102 catalogue products. Local conversation-write/rollback tests used disposable databases. The subsequent approved live run wrote four test-account messages to the supplied database and verified guest non-persistence. See `output/p8-local-verification.json` and the two `p8-*-local.png` screenshots for local evidence.

### Approved live evidence

The real-model run asked about pink while viewing Ua Gameday Double Knit Hood and saved the shopper’s stated navy preference. A fresh browser context signed into the same account, restored the conversation, and recalled navy plus the authenticated name/email. On the newly viewed Champion Reverse Weave Hoodie 1 page, the reply identified that item and its catalogue colors, rather than reusing the previous product. Refresh restored the second reply. SQLite contained both user/assistant pairs (four new rows); a separate logged-out guest turn returned the current product’s colors without adding history rows. Both test-account sessions were logged out afterward. No catalogue or inventory records were modified.

- [Live replies, saved rows, and checks](p8-memory-verification.json)
- [Current-item question](screenshots/p8-current-item-live.png)
- [Returning shopper and new product context](screenshots/p8-returning-customer-live.png)
- [Temporary guest chat on mobile](screenshots/p8-guest-live-mobile.png)

Rerun intentionally from `frontend/` with both servers running: `RUN_LIVE_CHAT=1 npx playwright test tests/memory-live.spec.ts`. This makes billable model calls containing the approved customer fields and writes test-account chat history. Ordinary test runs skip it.

## Problem 9 — Usability improvements

[usability.md](usability.md) is the main writeup: it records the two frontend and two backend choices, why each helps, how to try them, and their verification. It was started before building the features.

### Frontend behavior

Handsome Dan now offers three suggested-question buttons for browsing pages and three different ones for item pages. A click fills an editable draft and focuses the input; it never sends automatically or overwrites a nonempty draft. Loading/sending disables the buttons. Current page context is still resolved at send time, preserving P8 behavior during navigation.

Assistant replies use a small `ChatText` renderer for paragraphs, bold text, and simple bullet/numbered lists. React escapes every string. Unsupported Markdown, links, and raw HTML remain inert text; no `dangerouslySetInnerHTML` or third-party parser is used. Shopper messages stay literal. The prompt encourages concise, scannable replies using only that formatting vocabulary.

### New registered agent tools

| Tool | Arguments | Result and use |
| --- | --- | --- |
| `get_product_details` | `product_id`, optional `size` | `ProductDetailsResult` with `info: ProductInfoResult` and `stock: StockLookupResult`, both built from one fresh catalogue/inventory snapshot. Prefer for combined price/stock questions. |
| `find_alternatives` | `product_id`, required `size`, optional `max_price` | `AlternativeProductsResult`: up to four other items in the source garment family with positive inventory in the exact normalized size, within the inclusive USD budget if specified. |

The original three tools remain registered, bringing the total to five. `get_product_details` reuses the existing model constructors and missing-data semantics without calling two separate read functions. It records both lookup results, so the existing unknown-stock output validator still applies. Its model validator requires the info and stock product IDs/existence to agree. Actual price/stock values stay read-only and fresh.

`AlternativeProductsResult` extends the search-result fields from P7 (`query`, `size`, `max_price`, `in_stock_only`, `total_matches`, `products`) with:

| Field | Reason |
| --- | --- |
| `source_product_id` | Identifies the item the shopper wants alternatives to; it is excluded from every returned card. |
| `source_found` | Distinguishes an unknown source item from a real item with zero alternatives. |
| `matching_category` | Names the garment family used for matching, making the basis of similarity explicit. `null` for a missing source. |

Family normalization groups hoodie/hooded labels, T-shirts, long-sleeve shirts, crewneck sweatshirts, quarter-zip pullovers, and jackets; other garment labels require an exact normalized category match. It does not claim identical fit, material, or color. All source/candidate/stock records come from one read transaction. Alternatives sort by absolute price difference from the source, then price, name, and ID; the first four are returned while `total_matches` counts all qualifying records. Missing size rows and zero quantities cannot qualify. Budgets are never silently raised. A missing source returns `source_found=false` and no cards.

The tool copies its search fields to `deps.last_search` for the existing `ChatReply.search` and saved history contract. Therefore its matches appear in the P7 results shelf with size/budget labels and working detail links. Empty alternatives replace old picks with the existing empty state. Its source metadata is retained only as tool context. If the model selects IDs outside the returned alternatives (including the original sold-out item), the output validator requests a correction and fails the turn safely if retries fail.

The prompt requires a stock lookup before saying the original item is sold out, and a known shopper size before finding alternatives. If size is unknown, ask. Zero alternatives should prompt an offer to adjust one constraint, not an automatic substitution outside the request.

### Verification

30 backend tests and 12 selected browser tests passed, along with the production build. Tests cover the single database read, fresh updates, unknown stock, exact size/budget/family filtering, exclusion of the original item, rejection of incorrect alternative picks, editable starters, navigation context, and HTML/link inertness. The formatting test includes incomplete markup so a partial bullet cannot hang the renderer.

The approved direct live run in [p9-agent-verification.json](p9-agent-verification.json) used one `get_product_details` call and two model requests to answer the source hoodie's $45 price and M quantity 8. The alternatives scenario used `get_stock` followed by `find_alternatives`, acknowledging L = 0 and returning only other hoodies with positive L stock under $70. The tool call counts demonstrate fewer steps for a combined lookup; total cost and latency still vary with prompt size, provider behavior, and retries.

P9 live browser verification passed: editable starters, bold prices/bulleted stock, desktop/mobile layout, and four L-in-stock alternatives under $70 were checked against catalogue records; an alternative card opened its full detail page. The search contained 18 total matches. Evidence: `output/p9-browser-verification.json` and `output/screenshots/p9-readable-chat-live-desktop.png`, `p9-readable-chat-live-mobile.png`, `p9-alternatives-live.png`. The initial browser test assertion was broadened to accept the clear equivalent “not in stock (0 available).” P9 live checks used guests and did not write account-history messages.

## Problem 10 — Storefront design

See [design.md](design.md) for the short visual rationale. `frontend/src/design.css` adds a campus field-journal theme, responsive product framing, and reduced-motion-aware transitions. The home page’s three campus-moment cards link to existing `?q=hoodie`, `?q=crewneck`, and `?q=football` catalogue searches. Product color captions use the existing database `colors` values. Mobile featured cards are a keyboard-accessible horizontal row with all three items available. Product detail routing, stock, and chat contracts are unchanged.

The production build and 12 existing browser checks passed. [Design verification](p10-design-verification.json) records checks at 320/390/768/1440 pixels, collection navigation, keyboard scrolling, and reduced motion. Screenshots under `screenshots/p10-*` show the running UI; no new model call was needed.

## Problem 12 — Current system reference

This section is the current reference for the running HW4 application and supersedes earlier shorthand where behavior has since grown. The supplied database and original product photos remain local under `data/`; `.gitignore` excludes them. The requested audit file is safe operational metadata and contains no raw shopper conversation.

### Request path and files

The React/Vite/TypeScript storefront calls the same-origin `/api` routes (`frontend/src/api.ts`); Vite proxies them to FastAPI on port 8000. `backend/main.py` authenticates the session, validates the request and current product-page ID, then calls `ShopChat.reply`. The agent in `backend/agent.py` loads `backend/prompts/prompt.md`, runs PydanticAI agent `handsome_dan`, and returns the structured `AgentReply`. Registered tools read current catalogue and inventory rows from SQLite in read-only mode. The server resolves selected product IDs back to verified database cards and returns `ChatReply`; the page displays its reply and matching product cards. A returned search replaces the visible shelf, and its cards use the same product-detail route as catalogue cards.

| File | Current responsibility |
| --- | --- |
| `backend/main.py` | FastAPI app, catalogue/image/chat/history routes, request protections, lifecycle wiring. |
| `backend/agent.py` | Lazy Portkey client/model, PydanticAI wiring, page/customer context, output checks, in-memory guest history, rate/concurrency/usage limits, timeout. |
| `backend/tools.py` | Read-only catalogue and inventory functions, matching, normalized sizes, tool dependencies/results. |
| `backend/models.py` | Validated database, agent, API, customer, page, and history data contracts. |
| `backend/history.py` | Additive schema setup and account-scoped chat storage; never an agent tool. |
| `backend/auth.py` | Signup/login/session protection and narrowly scoped account writes. |
| `backend/audit.py` | Append-only JSON-array audit records, catalogue-vocabulary argument filtering, and safe result summaries. |
| `backend/prompts/prompt.md` | Handsome Dan’s voice, tool policy, truthful inventory, privacy, and content/image safety rules. |

The model is exactly `gpt-5.6 luna` through Portkey (`https://api.portkey.ai/v1`, OpenAI provider). `PORTKEY_API_KEY` is read by `backend/agent.py` from the parent project's root `.env` or an already-set environment variable. Client construction is lazy, so browsing/auth do not need a key. The key never reaches the browser, prompt, reply, or audit record. The system prompt is read when the agent is first constructed; restart the backend after changing the prompt or key.

### `models.py` fields and why they exist

The models constrain both agent data and the API. Counts and prices use numeric validation; stock statuses and page/role/currency values use literals; extra page/request fields are forbidden where client input could otherwise smuggle unvalidated context. Validators enforce the listed relationships.

| Model | Fields and purpose |
| --- | --- |
| `Stock` | `size`: exact inventory size key; `quantity`: nonnegative recorded units. |
| `ProductInfo` | `product_id`: stable lookup key; `name`: shopper-facing label; `description`: catalogue text; `garment_type`: category; `colors`: recorded product colors; `price`: finite nonnegative DB price; `currency`: fixed `USD` because the source schema has no currency column. |
| `ProductInfoResult` | `product_id`: requested key even on misses; `found`: separates a real match from missing data; `product`: nullable typed record. Validator requires `found` and `product` to agree and IDs to match. |
| `SizeStock` | Inherits `size` and `quantity`; `status`: `in_stock` or `out_of_stock`, validated against whether quantity is positive. |
| `StockLookupResult` | `product_id`, optional `product_name`, and `requested_size` identify the lookup; `status` distinguishes positive stock, recorded zero, an unlisted size, missing product, and absent inventory; nullable `quantity` avoids pretending unknown is zero; `sizes` carries exact per-size rows. Validator requires totals/status to agree and prevents unknown states from carrying quantities. |
| `ProductCard` | `product_id`, `name`, `garment_type`, `description`, `colors`, `search_tags`, `image_url`, `price`, `inventory`: all fields needed for a matching storefront card and its detail view. The backend fills these fields from SQLite; the model selects IDs, not card contents. |
| `ProductSearchResult` | `query`, optional `max_price` and `size`, `in_stock_only`: preserve applied search/filter context; `total_matches`: exact count before display cap; `products`: at most six card records. |
| `ProductDetailsResult` | `info` plus `stock`: one combined answer contract for a single database snapshot; validator requires matching IDs and product-existence state. |
| `AlternativeProductsResult` | Extends search fields; `source_product_id` and `source_found` identify the source; `matching_category` records the family matched. Its `products` cap is four. |
| `CustomerContext` | `name`, optional `first_name`, and `email`: only authenticated profile values explicitly passed for personalization/account questions; it has no ID or credential field. |
| `PageContext` | `page`: constrained route label; optional `product_id`: identifies “this item” only on product pages. Validator requires an ID exactly on product pages, with syntax/length limits. The server also checks catalogue existence. |
| `ChatRequest` | `message`: trimmed nonempty text capped at 1,000 characters; `page_context`: validated current route/product reference. Extra fields are forbidden so callers cannot supply an identity. |
| `AgentReply` | `reply`: shopper-facing text, 1–2,500 characters; `product_ids`: at most four IDs selected from records seen through tools. Output validation rejects unverified IDs and the backend constructs actual cards. |
| `ChatReply` | `reply`: final message; `products`: verified compact chat picks; optional `search`: latest page shelf result. |
| `ChatMessage` | `role`: only `user`/`assistant`; `content`: history text; `products` and `search`: saved display snapshot; optional `page_context`: page attached to the user turn. |
| `ChatHistory` | `messages`: validated history collection returned by the history endpoint. |

Authentication has separate `PublicUser`, `LoginInput`, and `SignupInput` contracts in `backend/auth.py`. `PublicUser` intentionally has no password/hash or session token; login/signup use `SecretStr`, and confirmation is checked but never stored. These account contracts are never registered as agent tools.

### Catalogue tools and result caps

All five tools are read-only and are registered with the PydanticAI agent. `read_products` opens SQLite with `mode=ro`; a SQLite authorizer permits reads only from `catalogue` and `inventory`. It cannot read users, password hashes, session records, or chat history. Tool arguments are model-generated but are validated/normalized by their function; facts are re-read for each call.

| Tool | Arguments and behavior | Result / limit |
| --- | --- | --- |
| `search_products` | `query` short catalogue keywords; optional inclusive USD `max_price`; optional normalized `size`; `in_stock_only` filter. | `ProductSearchResult`: exact `total_matches`, applied filters, at most 6 cards, ordered by price/name. A requested size must have an inventory row; in-stock-only requires quantity > 0. |
| `get_product_info` | Exact `product_id`; search first if the ID is unknown. | `ProductInfoResult`: current price, description, type, and colors, or `found=false`. |
| `get_stock` | Exact `product_id`; optional requested `size` (omit only for overview). Common size names normalize to database size labels. | `StockLookupResult`: per-size counts; zero is explicitly out of stock; missing size/inventory/product has a distinct status and null quantity. An all-size quantity is a sum, not a per-size count. |
| `get_product_details` | Exact `product_id`; optional size. | `ProductDetailsResult`: current product facts and stock from one read snapshot; prefer for combined price/availability. |
| `find_alternatives` | Exact source `product_id`, required size, optional inclusive `max_price`. | `AlternativeProductsResult`: up to 4 different products in the same normalized garment family with positive quantity for that exact size; exact total count; original excluded. It never silently relaxes size or budget. |

The agent may select at most four verified `product_ids` for chat cards. Page search cards are produced from the tool's `ProductSearchResult.products` (up to six). Search/category results replace the previous shelf; empty matches return an empty shelf. Product cards, including cards found through chat, open the same full item detail route.

### Safety boundaries

- `prompt.md` requires a friendly, concise campus-store voice; polite language; no profanity, slurs, harassment, insults, or demeaning text. A refusal is brief and does not repeat offensive wording.
- Shopper text, saved chat, and product text are untrusted data, not instructions. The agent declines prompt disclosure, hidden reasoning, credential requests, arbitrary SQL/code/browsing, harmful requests, and account access outside the website.
- The agent uses only supplied catalogue images. It must not invent, fetch, generate, substitute, or claim to modify/verify photos; it does not reveal image paths or internal image metadata. Image/data text is not an instruction.
- Price, sizes, and stock claims require a current tool result. Recorded zero is sold out; a missing row is unknown. Tool errors and absent data are acknowledged rather than filled in.
- SQLite tool access is read-only and table-limited. The agent has no account, session, password, arbitrary-SQL, shell, or file tool. Authenticated name/email enter only the current dynamic customer context; IDs, passwords, hashes, cookies, and token digests do not.
- FastAPI checks allowed Origin plus `X-Requested-With: CampusCustoms` for mutations, uses HttpOnly/SameSite cookies, and returns generic validation errors instead of submitted values. Passwords use salted scrypt; session tokens are random and only their SHA-256 hashes are stored.
- The frontend renders assistant formatting with escaped React text; it does not treat reply HTML as executable markup. The image endpoint serves only `data/products/`.

### Audit trail format and retention

FastAPI creates `output/audit_trail.json` if it is absent, starting with a JSON array. `backend/audit.py` appends `turn_started`, `tool_started`, `tool_completed` or `tool_failed`, and `turn_stopped` objects. Each has a UTC timestamp and a random per-turn `run_id`. File and thread locks serialize writers; each update validates the existing array and refuses to overwrite malformed data. Existing event objects are retained across app restarts; there is no reset or rotation. The file is mode-restricted on creation and grows with use.

Tool arguments are bounded summaries: product IDs are kept only when present in the catalogue, search keywords are filtered against catalogue vocabulary, sizes are normalized to known values, budgets are numeric, and flags are booleans. Results contain typed status/count/price/quantity summaries and catalogue IDs, never descriptions or images. Tool failures record only the exception class. Turn stop reasons are fixed operational categories; token/request/tool counts are included when available. No customer/session IDs, names, emails, cookies, passwords, hashes, raw user messages, assistant replies, prompts, hidden reasoning, API keys, image URLs/paths, or raw exception text are recorded. These summaries may still reveal which catalogue item was looked up and its price/availability; keep the generated operational log with the private project data and review it before publishing.

A representative record sequence (values are illustrative):

```json
[
  {"time":"2026-10-01T12:00:00.000Z","event":"turn_started","run_id":"a1b2c3d4","model":"gpt-5.6 luna","page":"products","limits":{"requests":5,"tool_calls":4,"total_tokens":20000,"completion_tokens":1200,"timeout_seconds":60}},
  {"time":"2026-10-01T12:00:01.000Z","event":"tool_started","run_id":"a1b2c3d4","tool":"search_products","args":{"query_terms":["hoodie"],"query_terms_omitted":0}},
  {"time":"2026-10-01T12:00:01.100Z","event":"tool_completed","run_id":"a1b2c3d4","tool":"search_products","result":{"match_count":12,"product_ids":["catalogue-id"]}},
  {"time":"2026-10-01T12:00:02.000Z","event":"turn_stopped","run_id":"a1b2c3d4","stop_reason":"completed","requests":2,"tool_calls":1,"input_tokens":800,"output_tokens":130}
]
```

### Runtime limits and routes

| Area | Current specification |
| --- | --- |
| Model loop | `UsageLimits(request_limit=5, tool_calls_limit=4, total_tokens_limit=20000)`; one PydanticAI retry; model completion cap 1,200 tokens; model client timeout 25 seconds, zero SDK retries; whole turn timeout 60 seconds. |
| Concurrency and rate | At most 4 active chat turns per process; one active turn per account/guest conversation; 15 messages per account or guest direct IP per 10 minutes. Guest memory: at most 100 conversations, six turns each, 30-minute inactivity expiry. |
| Chat payload/history | Input 1,000 characters; account history endpoint returns up to 100 messages; model receives up to six prior turns. Guest history remains in process memory only. |
| Product output | 6 search cards, 4 alternative cards, at most 4 agent-selected chat-card IDs. Unknown inventory never becomes a guessed zero. |
| Authentication | Signup/login limit 30 attempts per direct IP per 10 minutes; session cookie lasts 7 days. Signup password length 12–128; names at most 80; login supports the seeded legacy credential. |

| Route | Purpose |
| --- | --- |
| `GET /api/products` | Full public catalogue cards with inventory snapshot. |
| `GET /api/products/{product_id}` | One public item or 404. |
| `GET /api/images/{path}` | Original supplied product image only. |
| `POST /api/chat` | Guest or signed-in agent reply and optional structured cards/search. |
| `GET /api/chat/history` | Up to 100 messages for the signed-in account; guest gets only its current temporary history. |
| `POST /api/auth/register` | Create account and session; confirmation is not stored. |
| `POST /api/auth/login` | Verify account and issue session. |
| `GET /api/auth/me` | Return current public profile. |
| `POST /api/auth/logout` | Revoke current session and clear cookie. |

Signed-in user/assistant turns are saved atomically in `chat_messages`, keyed by authenticated `user_id`; saved rows persist through backend restarts and are not available to the agent as an unrestricted table. Guest history is temporary, isolated from accounts, and is never inserted into SQLite. The local database holds account and history data, so it remains private and ignored by Git.

### Run the application

From the homework folder, install the dependencies once if needed:

```sh
.venv/bin/python -m pip install -r requirements.txt
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

In a second terminal:

```sh
cd "HW 4/frontend"
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards `/api` to `http://127.0.0.1:8000`; FastAPI docs are at `http://127.0.0.1:8000/docs`. The database and `data/products/` must be supplied locally. Browsing and accounts can run without the model key; agent chat requires `PORTKEY_API_KEY` in the parent root `.env` or process environment. The FastAPI development command is a single-process local configuration; rate limits and in-process guest/concurrency state need shared services before multi-worker deployment.
