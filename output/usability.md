# Problem 9 — Campus Customs usability improvements

Started before implementation and updated after verification. All four improvements below are implemented in the running shop at http://127.0.0.1:5173. The changes build on the existing catalogue, account memory, and product detail pages.

## Frontend 1 — Page-specific conversation starters

**What:** Add keyboard-accessible prompt buttons in Handsome Dan’s panel. Browsing pages offer hoodie, budget, and size searches; product pages offer the current item’s price/stock, colors, and similar items in medium. Selecting a button fills an editable draft instead of sending an unexpected request. Buttons are disabled while loading/sending and never overwrite an existing draft.

**Why:** New shoppers do not have to guess what the assistant can do. The prompts lower typing effort on phones and connect product-page questions to the item actually being viewed. Draft preview lets shoppers change size or budget before sending.

**Try it:** Open chat on Home, choose “Hoodies under $70,” edit if desired, and send. Open an item and check that the suggestions change.

## Frontend 2 — Readable, safely formatted replies

**What:** Render assistant paragraphs, simple bullet/numbered lists, and bold emphasis as React elements. Keep shopper text literal. Raw HTML and links remain non-executable text; no HTML injection API or new dependency is needed. Increase chat text spacing, wrap long text, and keep the panel usable on narrow screens.

**Why:** The current live replies sometimes show literal `**` markers and dense text. Readable price/stock answers are easier to scan, while inert markup prevents product text or model output from inserting scripts into the storefront.

**Try it:** Ask for a short list of available sizes and exact prices. Prices emphasized with `**` should appear bold, and lists should be visibly separated.

## Agent/backend 1 — Price and stock in one fresh lookup

**What:** Add `get_product_details(product_id, size?)`, returning typed product information and exact stock from the same SQLite read. Update the prompt to prefer this tool for combined price-and-stock questions; keep the dedicated tools for narrower questions.

**Why:** A shopper asking “How much is this and do you have medium?” should get one coherent answer. One combined tool replaces two separate database reads and can avoid one sequential model round trip. It retains the distinction between sold out and missing inventory rather than guessing quantities. Actual timing and cost depend on the model; no percentage saving is assumed.

**Try it:** On the Ua Gameday Double Knit Hood page, ask for the price and stock in medium. Compare the answer to the product detail view.

## Agent/backend 2 — Useful alternatives with real size stock

**What:** Add `find_alternatives(product_id, size, max_price?)`. It excludes the current item, matches its garment family, requires positive stock in the exact normalized size, respects any stated budget, and returns up to four verified cards. Order alternatives by closeness to the source price. Results use the existing dynamic shelf and full item links. Empty results are explicit, with no silent relaxation of size/budget.

**Why:** A sold-out size should not leave a shopper at a dead end. Relevant, available alternatives help the shopper keep browsing and help the business retain interest without making false availability claims. The tool is also useful when a shopper simply wants comparable styles.

**Try it:** On Ua Gameday Double Knit Hood, ask “Is large in stock? If not, find similar hoodies in large under $70.” Its recorded L quantity is zero; the reply should acknowledge that and offer only matching alternatives with L stock.

## Verification

**Passed:** 30 backend tests, 12 local browser checks, the TypeScript/Vite production build, two direct real-model scenarios, and one real browser test covering all four improvements.

| Improvement | What was actually verified | Evidence |
| --- | --- | --- |
| Frontend 1: conversation starters | A button created an editable draft without sending; keyboard activation focused the input; a nonempty draft disabled the buttons; product-page suggestions replaced browsing suggestions. The live browser used both the price/stock and alternatives starters. | `frontend/tests/usability.spec.ts`, [live browser results](p9-browser-verification.json), [mobile starters (local test)](screenshots/p9-starters-mobile-local.png) |
| Frontend 2: readable replies | The real price appeared bold and size stock appeared as list items on desktop/mobile. Tests confirmed raw HTML, `javascript:` links, and shopper Markdown stayed inert; incomplete bullet markup did not hang the page. | [Desktop answer](screenshots/p9-readable-chat-live-desktop.png), [mobile answer](screenshots/p9-readable-chat-live-mobile.png) |
| Backend 1: combined lookup | The actual model selected `get_product_details` once, returning $45.00 and M = 8. The run used two model requests (tool selection, then answer). A local test counted one database read and verified that a subsequent lookup reflected changed test data. Missing sizes stayed unknown. | [Tool names, request counts, and exact lookup values](p9-agent-verification.json) |
| Backend 2: available alternatives | The actual source had L = 0. The live reply acknowledged that, then displayed four other hoodies from 18 qualifying alternatives, all with positive L stock and prices no higher than $70. The browser compared every returned card with its catalogue API record and opened an alternative’s full detail page. | [Alternative cards and filters](screenshots/p9-alternatives-live.png), [live browser results](p9-browser-verification.json) |

The first browser assertion accepted only “sold out”/“out of stock” and rejected the equally clear reply “not in stock (0 available).” The assertion was corrected to accept that wording; the completed live browser run passed. This did not require changing the product facts or weakening the size/budget checks.

### Files and contracts

- Frontend: `frontend/src/main.tsx` supplies the starters, `frontend/src/ChatText.tsx` renders safe text formatting, and `frontend/src/styles.css` defines the navy/cream chips, spacing, and mobile layout.
- Backend: `backend/tools.py` implements both tools; `backend/models.py` defines `ProductDetailsResult` and `AlternativeProductsResult`; `backend/agent.py` registers them and rejects recommendation IDs outside the returned alternatives; the same `backend/prompts/prompt.md` explains when to use them.
- [Harness](harness.md#problem-9--usability-improvements): model fields, exact filtering rules, and response flow into the existing cards.

### Reproduce the checks

With both servers running, from `frontend/`:

```sh
npm run build
npx playwright test tests/storefront.spec.ts tests/chat.spec.ts tests/search.spec.ts tests/memory.spec.ts tests/usability.spec.ts
```

From the homework folder, run `.venv/bin/python -m unittest discover -s backend/tests -v` for the local backend suite. These tests use disposable databases and mocked model responses; they do not incur model charges.

For the approved **real** model checks, run `.venv/bin/python -m backend.tests.verify_p9` from the homework folder and `RUN_LIVE_CHAT=1 npx playwright test tests/usability-live.spec.ts` from `frontend/`. These intentionally call Portkey. P9 live verification uses guest context and creates no account-history messages. Database and source product images remain excluded from Git.

### Practical limits

The combined tool reduces the required lookups for a combined question, but more registered tools and prompt text also contribute tokens; total dollar savings are not guaranteed. The existing request, token, and rate limits still apply. Similarity uses explicit garment families, not a fit/style guarantee, and the alternatives tool does not infer color preferences. Stock is a database snapshot, not a reservation. Only paragraphs, bold text, and simple lists are formatted; unsupported markup remains readable literal text.
