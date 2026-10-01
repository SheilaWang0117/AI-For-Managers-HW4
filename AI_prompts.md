# HW4 — Campus Customs: AI Prompts

Public-repository note: the private data pack, local `.env`, and run-generated verification files are excluded. The P4 prompt below redacts its sample password. Opt-in live-call scripts are not included in this public copy.

## Problem 1 — Start the project prompt log

### Prompt typed

> hi, today we will be making a campus customs shop and chatbot project, this is hw4, so put all the work in the hw4 folder. so for this hw we need to create a real custoer website with helpful chatbot for campus customs. we will create a react + vite typescript front end and a python fast API backend whose brain is pydantic ai agent. shoppers should be able to browse products and create an account, chat about merch, see matching items appear on the page get honest answers abt price & stock from local database. in the data folder, you have campus\_customs.db with tables for product catalogue, iventory size, users with hashed passwords. product image file paths are in ctalogue table. you can also look at yalebulldogblue.com to learn the style of campus customs page and info for agent prompt (I would say use navy blue and yale colors, with cute bulldogs woudl be nice. we will do this one problem at a time with each problem keeping track like how we used to do. at the end we will push this to a public github repo and submit repo URL on canvas. dont commit database or product images. ok now for problem1, create AI\_prompts.md keep it updated as we work, logging all we typed tlike what we always did, put one section for each problem with problem number and title, at least one prompt iv e typed, one followup prompt if needed and one sentence on what was lacking after the first, running site, databse writes, screenshots are evidence, no need extra proff essay beyond these prompts

### Follow-up prompt

None yet.

What was lacking after the first prompt: no implementation feedback has been given yet; this step establishes the log, and the website and chatbot will be built in later problems.

### Evidence

- `AI_prompts.md` — this prompt log.
- `.gitignore` — excludes local data, database files, product images, secrets, and generated environments.

Keep adding one section per assigned problem with its number and title, actual user prompts and follow-ups, and one sentence about what needed improvement. Link actual running-site evidence, database writes, or screenshots when available; no separate proof essay is needed.

## Problem 2 — Analyze the database

### Prompt typed

> NOW FOR P2, WE WILL ANALYZE THE DTABASE. LOOK AT THE DATABASE DATA/CAMPUS\_CUSTOMS.DB, PLEASE STRART TRYING TO FIGUREOUT THE FIELDS OF EACH TABLE, AT A MINIMUM WE NEED TO UNDERSTAND CATALOGUE, INVENTORY, AND USERS, startt the file ouotput/harness.md, write down each table n its fields and one short line on why each field matters for the shop or the chatbot, we will keep growing this harness file in later problems (models, tools,safety, sepcs).

### Follow-up prompt

None yet.

What was lacking after the first prompt: no follow-up correction has been requested; the initial inspection also identified saved chat messages and SQLite's internal sequence table, so both are included alongside the three required tables.

### Evidence

- `output/harness.md` — every table and field, types, constraints, purpose, relationships, and observed data formats.
- Read-only SQLite inspection: 102 products, 612 inventory rows, 3 users, and 22 messages; all 102 image paths resolve under `data/`, the foreign-key check found no violations, and the database quick check returned `ok`.

## Problem 3 — Build the Campus Customs storefront

### Prompt typed

> ok now for p3 we will build the campus customs website, scaffold a react + vite + typescript front end for campus customs. put a nav bar at the top that links to the mainpages such as home, products, abt us, login, create account. youcan pull campus custons-style wording from yalebulldogblue.com for home and abt us, but we should write theses pgaes in our own voice and not copy from the original site text. now on the products page, show product images from the catalogue (use image paths in the database), with basic product info (name, price, short description). please make each product open a single item page, so large image on one side, full product etxt on the other including description, price, sizes/stock when u have them, be creative. clicking a card on products should take shoppers there. also add chat interface at the bottom right of the site (a floating chat panel with bulldog logo on it), it does not need to talk to agent yet, a stub that will call ur backend later is enough for this problem. we will need a small API soon in order to read the database. its fine to start a simple FastAPI app in backend/main.py just to serve products and images, then growing it into the agent backend in P5

### Follow-up prompt

None yet.

What was lacking after the first implementation: the initial featured photos had black backgrounds that looked awkward in the hero, so other original catalogue photos were selected; browser checks also needed to wait for React's filter updates.

### Evidence

- `frontend/` — routed storefront, product filters and details, account preview pages, and floating bulldog chat preview.
- `backend/main.py` — read-only product and image endpoints backed by the supplied SQLite database.
- `output/screenshots/` — desktop home, product listing, item detail, mobile home, and mobile chat screenshots.
- `output/harness.md` — architecture, endpoints, current limits, and verification notes; `README.md` — local run instructions.
- Validation: TypeScript/Vite production build passed and all five Playwright browser/API tests passed; no database writes or AI calls.

## Problem 4 — Create accounts and log in securely

### Prompt typed

> this is so cute, great job!, now for problem 4 we are creating account and login, first build a normal create-account/lpgin flow, create account: first name, last name, email, password (confirm password is a nice touch), login : email and password, make it cuete wit bulldogs. go to he users table, make sure to store passwords securely so hackers both human or AI can't access them. the seed database already have a test user you can use while building: includ email: test\@campuscutoms.yale.edu, password: [redacted sample password], confirm that you can login as this user and brand new account we. create also works. update the output/harness.md with how auth works (like what u store for a user and how passowiords are protected.

### Follow-up prompt

None yet.

What was lacking after the first implementation: browser checks caught an ambiguous password label caused by the show/hide button, so the input now has an explicit label separate from the button.

### Evidence

- `backend/auth.py` — signup, seed-compatible login, password hash upgrades, cookie sessions, and logout.
- `frontend/src/auth.tsx`, `frontend/src/api.ts`, `frontend/src/main.tsx` — working account forms and session-aware navigation.
- `backend/tests/test_auth.py` — authentication checks using an isolated temporary database.
- `output/auth-verification.json`, `output/screenshots/p4-*.png` — synthetic account and running-site evidence, with no saved passwords or session tokens.
- `output/harness.md` — user fields, password protection, session storage, endpoints, and current limits.

The supplied seed account's actual address is `test@campuscustoms.yale.edu`; the prompt's address contains a typo. No existing account email or password was changed to match that typo.

Verified: seed login succeeded, a new synthetic account was saved and could log back in, all six backend and seven browser/API tests passed, and the production build passed. Database inspection confirmed hashed passwords and revoked test sessions; no model calls were made.

## Problem 5 — Connect the PydanticAI shop agent

### Prompt typed

> ok now for p5, we will be doing pydanticAI agent backend. first create shop chatbot as pydanticai agent behind FastAPI, logged into the front end chat widget. put API app in backend/main.oy, the file you run with Uvicorn. keep agent as these four files next to it. . this should include backend/prompts/prompt.md (system prompt and grow this same file later), backend/agent.py, agent entry/wiring, backend/tools.py, tools the agent can call, backend/models.py pydantic/pydanticai sturctued types. in main.py expose chat route so a message from the website returns a reply from the agent (and whatever u need for products). u will need the AI model API key for the agent. puut campus customs voice and safety basics into oompts/prompt.md (we will expand tools and safety later). start or update types in models.py for chat replies/ product cards as needed. In output/harness.md note how the front end talks to fastAPI n how agent is loaded (prompt file and model), make sure backend runs from backend/ folder like: uvicorn main:app --reload --port 8000

### Follow-up prompt

> Approve HW4 chatbot model calls

This answer approved sending shopper messages and relevant product descriptions, prices, sizes, and stock to the configured Portkey model; account details, passwords, hashes, and session tokens remain excluded.

What was lacking after the first implementation: local tests caught that this PydanticAI version exposes usage as a property rather than a method, which was corrected before the approved live tests.

### Evidence

- `backend/main.py`, `backend/agent.py`, `backend/tools.py`, `backend/models.py`, `backend/prompts/prompt.md` — authenticated chat API and agent implementation.
- `frontend/src/api.ts`, `frontend/src/main.tsx` — chat requests, loading/errors, item cards, and recommendations on the page.
- `backend/tests/test_chat.py` — local PydanticAI tool and API checks using `FunctionModel` with no external calls.
- `frontend/tests/chat.spec.ts` — explicitly mocked UI checks; `output/screenshots/p5-chat-local-interface.png` is labeled as local test evidence, not a live model response.
- `output/harness.md` — architecture, prompt/model loading, response fields, safety boundaries, and limits.

Verification: 12 backend tests, seven selected local browser tests (catalogue and chat UI), one live signed-in browser test, and the production build passed. The requested Uvicorn command was started successfully from `backend/`. Automatic approval review initially blocked the live test because it would send local catalogue/inventory fields to Portkey; after the explicit approval above, both a direct agent run and the full website flow succeeded.

- `output/p5-agent-response.json` — real agent reply; the direct run used two model requests and one catalogue tool call.
- `output/p5-live-chat.json` — real browser/API/model result with price, size-stock, and reload checks.
- `output/screenshots/p5-chat-live-desktop.png`, `output/screenshots/p5-chat-live-mobile.png` — actual model response and recommendations in the running site.

## Problem 6 — Database tools for product information and stock

### Prompt typed

> now for p6, it will be our task to build tools: product info and stock. give the agent tools that look up actual info from campus\_customs.db such as product description, price, and how many are in stock (by the size when the customer asks)the agent must use databse, and hsould not invent prices or quantities. if a size is out of stock say so. exapnd prompts/prompt.md so that agent knowd to call these tools for price and sttock questions. add or update return types in models.py. in output/harness.md, list each tool and explain which model fields u chose for lookup results n why.

### Follow-up prompt

None needed so far.

What was lacking after the first implementation: a live reply called an unlisted size “not available,” so the prompt and output validator were strengthened to distinguish unknown availability from a confirmed stock shortage.

### Evidence

- `backend/tools.py` — dedicated product-info and size-stock lookups, with fresh SQLite reads and size normalization.
- `backend/models.py` — typed product lookup, per-size stock, and missing-data statuses with consistency validation.
- `backend/agent.py`, `backend/prompts/prompt.md` — registered tools, lookup instructions, and unknown-stock output checks.
- `backend/tests/test_chat.py` — exact prices, sold-out sizes, unlisted sizes, missing inventory/products, fresh reads after database changes, and contradictory-result rejection.
- `backend/tests/verify_p6.py`, `output/p6-lookup-verification.json` — live model checks with typed tool results and visible replies.
- `output/harness.md` — every active tool and lookup field explained.

Verified: all 18 backend tests passed; live tool calls returned the database's $45.00 price, M quantity 8, L quantity 0 with an explicit out-of-stock reply, and an unknown quantity for unlisted 3XL. The final live 3XL reply explicitly states that availability cannot be confirmed. No supplied database records were changed.

## Problem 7 — Handsome Dan’s chat search updates the page

### Prompt typed

> ok great!, now for p7, we wwill be doingchat search that updates the page. when a customer ask about a type of item such as what hoodies do u hav, agent should search the ctalogue and the website should dynamically show those matching items as product cards such as image, name, price, short info, make it cute, and make the agent name handsome dan. so the agent returns structured product matches n then the front end renders them on the website. after the dynamic product cards r loaded by new feature, make sure the same single item page bhaveior u built in p3 still works, so that each product card including the ones the chat just put on the page shoudl still open that detail view (large image + full info when clicked, update prompts/prompt.md and output/harness.md so its clear how search results reach the page

### Follow-up prompt

None needed.

What was lacking after the first implementation: the earlier chat cards hid short descriptions, did not distinguish an empty search from a conversational reply, and appeared above the full product detail view; P7 fixes those behaviors and names the assistant Handsome Dan.

### Evidence

- `backend/models.py`, `backend/tools.py`, `backend/agent.py` — typed search results and database-backed cards propagated into replies and history.
- `frontend/src/main.tsx`, `frontend/src/api.ts`, `frontend/src/styles.css` — Handsome Dan, dynamic result shelf, descriptions, counts, empty state, and shared product detail links.
- `backend/prompts/prompt.md`, `output/harness.md` — browsing instructions and search-to-page contract.
- `frontend/tests/search.spec.ts` — deterministic checks for replacement, thanks preserving results, history restoration, no matches, and page-card detail navigation.
- `frontend/tests/search-live.spec.ts` — opt-in real model/browser verification and screenshots.

Local verification: 20 backend tests, eight selected browser tests, and the production build passed.

Live verification passed: Handsome Dan found 27 hoodie matches and displayed six cards, all checked against catalogue records. Clicking a page card opened its full detail view with the recorded description, price, and size stock; mobile layout, Back, and refresh restoration passed. Evidence: `output/p7-search-verification.json`, `output/screenshots/p7-search-live-desktop.png`, `output/screenshots/p7-search-live-mobile.png`, and `output/screenshots/p7-search-product-detail.png`.

### P7 follow-up — Restart the website

> the website does not open

Both local development servers had stopped. Restarted Vite and FastAPI and verified that the homepage and proxied catalogue API returned HTTP 200 with all 102 products.

## Problem 8 — Customer memory and current-page context

### Prompt typed

> for p 8 we will be working on custoer memory, so when ah shopper is lgged in, save the chat history in the database in ana pproriate table and reload it when they treun. the agent should know who is chatting such as the name and emial and put that in agent deps (or equal clear pattern) or tools the agent can call, also pass enough page context that if a person is on product page and ask somthing like do you have this in pink? the agent knows which item they want, you can put code into agent context. guests can still chat, but history will only need to persist for logged in users. doc in output/harness.md how user chat history is stored and what customer fields the agent sees and how page context is passed

### Follow-up prompt

> yes u may

This approves including the signed-in shopper’s name and email in HW4 Portkey model calls and running the final P8 live test. Passwords, hashes, and session tokens remain excluded.

What was lacking after the first implementation: history was temporary and guest chat/context were missing; P8 testing also caught a fast-navigation race, fixed by reading the current route at send time.

### Evidence

- `backend/history.py` — additive migration of the existing `chat_messages` table, account-scoped reads, and atomic user/assistant writes.
- `backend/agent.py`, `backend/tools.py`, `backend/models.py` — persistent account memory, temporary guest memory, typed customer/page context, and dynamic agent instructions.
- `backend/main.py`, `frontend/src/api.ts`, `frontend/src/main.tsx` — verified account identity, guest cookies, page context on every message, and restored history in the widget.
- `backend/tests/test_chat.py` — disposable-database tests for persistence across service instances, account isolation, atomic rollback, guest non-persistence, context fields, and request validation.
- `frontend/tests/memory.spec.ts` — explicitly mocked UI checks and screenshots; these do not represent live model replies.
- `frontend/tests/memory-live.spec.ts` — live browser/model/database verification passed after the explicit name/email-to-Portkey approval above; saved evidence is in `output/p8-memory-verification.json`.

Final local verification: 26 backend tests and all 10 selected browser scenarios passed; the two memory scenarios each passed three consecutive runs after the navigation timing fix. The production build passed. The real database migration preserved all 22 existing chat rows and 102 catalogue products. Local conversation-write/rollback tests used disposable databases. The subsequent approved live run wrote four test-account messages to the supplied database and verified guest non-persistence. See `output/p8-local-verification.json` and the two `p8-*-local.png` screenshots for local evidence.

Live verification passed after “yes u may”: the test restored the conversation in a fresh browser login, recalled navy plus the authenticated name/email, used the newly viewed product instead of the preceding item, and restored history after refresh. Four account rows were written; the guest chat added no database rows. Both test-account sessions were logged out afterward. Evidence: `output/p8-memory-verification.json`, `output/screenshots/p8-current-item-live.png`, `output/screenshots/p8-returning-customer-live.png`, and `output/screenshots/p8-guest-live-mobile.png`.

## Problem 9 — Four usability improvements

### Prompt typed

> now we will work on p9 which is usability improvements. now the core shop is working we need to improve it by choose and implement 2 front end usability improvement s and 2 agent/backend usability improvement. front end improvements are things that make site look better and make it easier to use. agent/backend improvements r things that make the agent output better, more accurate or safer. these could be new agent tools or things that make agent run faster or cheaper write output/usability.md before or as you bild. for each of the improvements slike what u added and why it helps a campus customs shopper or the business. ,ake sure all improvements acc show up in the running app. these writeup and features are very important

### Follow-up prompt

None needed.

What was lacking after the first implementation: shoppers had to compose every question from scratch, replies showed literal Markdown markers, combined price/stock questions needed separate lookups, and sold-out sizes had no dedicated, constrained alternative-finding tool.

### Evidence

- `output/usability.md` — written before implementation, with two frontend and two backend choices, their shopper/business benefits, and reproduction steps.
- `frontend/src/ChatText.tsx`, `frontend/src/main.tsx`, `frontend/src/styles.css` — editable page-specific prompt buttons and readable, safely rendered chat text.
- `backend/tools.py`, `backend/models.py`, `backend/agent.py`, `backend/prompts/prompt.md` — one-snapshot price/stock lookup, size-and-budget-constrained alternatives, typed results, and output checks.
- `backend/tests/test_chat.py`, `frontend/tests/usability.spec.ts` — local tool, interaction, and safe-formatting verification.
- `backend/tests/verify_p9.py`, `output/p9-agent-verification.json` — approved real-model tool choices and request counts.
- `frontend/tests/usability-live.spec.ts` — real browser flow and screenshot evidence.

Local verification: 30 backend tests, 12 selected browser checks, and the production build passed. The live combined question used `get_product_details` once and two model requests; the live sold-out-size question used `get_stock` then `find_alternatives` with three model requests.

P9 live browser verification passed: editable starters, bold prices/bulleted stock, desktop/mobile layout, and four L-in-stock alternatives under $70 were checked against catalogue records; an alternative card opened its full detail page. The search contained 18 total matches. Evidence: `output/p9-browser-verification.json` and `output/screenshots/p9-readable-chat-live-desktop.png`, `p9-readable-chat-live-mobile.png`, `p9-alternatives-live.png`. The initial browser test assertion was broadened to accept the clear equivalent “not in stock (0 available).” P9 live checks used guests and did not write account-history messages.

## Problem 10 — Creative storefront design

### Prompt typed

> for p 10 we  will be styling the website, now add creative design so the site feels like a real campus customs storefront like fonts, color hierarchy, motion product presnetation, chat feel, so far its pretty good i would say, the more innovative design the better. write output/design.md what we changed and why it should help customers stick around and buy. keep iot concrete and short

### Follow-up prompt

None needed.

What was lacking after the first implementation: the functional storefront needed a more distinctive visual identity, occasion-based collection entry points, and consistent product/chat styling; the old mobile featured grid also hid the third item.

### Evidence

- `frontend/src/design.css` — campus field-journal styling, color/type hierarchy, product presentation, restrained motion, and reduced-motion support.
- `frontend/src/main.tsx` — linked campus-moment collections, database color labels, photo captions, and Handsome Dan name labels.
- `output/design.md` — short design rationale and intended shopping benefits.
- `output/p10-design-verification.json` — 20 layout checks across five pages/four widths, three working collection links, mobile keyboard scrolling, reduced motion, and no page errors.
- `output/screenshots/p10-home-desktop.png`, `p10-home-mobile.png`, `p10-campus-moments.png`, `p10-product-detail.png`, `p10-chat-desktop.png`, `p10-chat-mobile.png` — running-site screenshots. Chat shows the guest interface; no model calls were needed for styling verification.

Verified: the production build and all 12 selected existing browser checks passed. New collection links, all 102 products, item pages, size stock, chat, and account UI remain usable. Database records and source product photos were not changed.

## Problem 11 — Live site app check

### Prompt typed

> for p11 we  will be working on site testing (app check). First, lets test the live site and doc it in output/app\\_check.html, which si a page that we can double click open. Place clear screen shots and short captions for, 1. Chat checking the inventory level of an item (the honest stock/price from the DB), 2. The dyamic search result cards appearing after a category questions such as hoddies. 3. One of the usability features u have added in p9( or maybe we did it earlier). Make the HTML easy to grade such as heading for each check, screen shot, one or two wentences on what the secreenshot proves, we need to put the screenshot image files in output/app\\_check\\_images. And link them from app\\_check .html with relative paths such as app\\_check\\_images/inventory.png

### Follow-up prompt

None needed.

What was lacking after the first implementation: the live app had not yet been checked with one self-contained grading page and labeled screenshots for inventory, chat search cards, and a usability feature.

### Evidence

- `output/app_check.html` — standalone, double-clickable page with one headed section and concise evidence caption for each requested check; image links are relative.
- `output/app_check_images/inventory.png` — live price and size-M stock reply beside the product page.
- `output/app_check_images/category-search.png` — six live hoodie cards from 27 database matches.
- `output/app_check_images/p9-prompt-starter.png` — product-specific prompt button filling an editable draft.
- `output/p11-app-check-verification.json` — values, search results and successful live checks; an offline file:// browser check confirmed all three relative screenshots load.

Verified October 1, 2026: the real live browser flow passed, matching price/stock to the API and every displayed search card to the catalogue API. Both FastAPI and Vite were running at capture time.

## Problem 12 — Audit trail, safety, and finished harness

### Prompt typed

> Now for p12, we need to audit trail, safety , finish harness, forist, keep an append only output/audit\_trail.json of agent loop activity such as time, tool name, short args/result, stop reason). Don’t wipe it between runs and also think abt some sfety rules to give tge agent and put them in prompts/prompt.md, something I think abt is to keep the images safe, dio not miss us ethe images provided, no bad words, always be polite etc. Finish output/harness.md so it is clear on how the system works, model fields in models.py and why u chose them, tools and abilities, safety rules, specs(loop limits, result caps, models, how to run front & back)

### Follow-up prompt

None yet.

What was lacking after the first implementation: agent turns had operational count logs but no durable per-tool audit trail, and the harness had accumulated implementation notes without one authoritative current system reference or explicit image and language rules.

### Evidence

- `backend/audit.py` and `output/audit_trail.json` — append-only JSON-array event log with bounded, privacy-minimized turn and tool records.
- `backend/prompts/prompt.md` — explicit original-image handling, untrusted-data, respectful-language, privacy, and truthful-inventory rules.
- `output/harness.md` — P12 current reference for request flow, every model field, tools, safety boundaries, caps, audit format, endpoints, and run commands.
