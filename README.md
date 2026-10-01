# Campus Customs — HW4

A Yale-inspired Campus Customs storefront built with React, Vite, and TypeScript, backed by FastAPI and a PydanticAI shopping assistant named Handsome Dan. Shoppers can browse the local catalogue, create an account, sign in, and ask about products, prices, and size-level stock. The app is a class project; checkout is not implemented.

## Before you run it: add the private data pack

The public GitHub repository intentionally does not include the supplied data pack. Obtain the course-provided `campus_customs.db` and product images separately, then arrange them like this inside the cloned `hw4/` folder:

```text
hw4/
  data/
    campus_customs.db
    products/
      <the original product image files referenced by the catalogue>
```

Keep the database at `data/campus_customs.db` and preserve the image filenames and `data/products/` directory. The catalogue stores those image paths, and the API serves only files from `data/products/`. Without the data pack, the backend cannot serve products, authenticate accounts, or answer inventory questions. These files are excluded by `.gitignore`; do not add them to Git.

## Configure the AI key

From the `hw4/` directory, make a local environment file:

```sh
cp .env.example .env
```

Edit `.env` and replace the placeholder with your own `PORTKEY_API_KEY`. The app uses the `gpt-5.6 luna` model through Portkey. The key stays on the backend; do not place it in a `VITE_` variable or commit `.env`. Browsing and account pages can start without a model key, but chat requires one. The backend also accepts `PORTKEY_API_KEY` from the process environment or the parent workspace's root `.env` file.

## Install and run

Use Python 3.10 or newer and Node.js 22.12 or newer. From the `hw4/` project root, create the local Python environment and install backend dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

In one terminal, start FastAPI from `backend/`:

```sh
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

In a second terminal, start Vite from `frontend/`:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Vite forwards `/api` requests to FastAPI at port 8000. FastAPI's interactive API page is at http://127.0.0.1:8000/docs. Stop each development server with Ctrl+C in its terminal.

## What the app does

- The storefront includes home, catalogue, about, login, signup, and product-detail pages. Catalogue cards and chat search cards open the same product-detail page.
- Product names, descriptions, photos, prices, colors, and size inventory come from the private local database and supplied images.
- The floating chat panel sends messages and current page context to FastAPI. Handsome Dan uses read-only catalogue tools and returns verified product matches for display on the page.
- New account passwords are stored as salted scrypt hashes. Signed-in chat history is stored by account in SQLite; guest history is temporary.
- `output/app_check.html` is a standalone grading page with screenshots linked relative to its location. `output/harness.md` describes the database, model fields, tools, safety boundaries, result caps, and run limits. `AI_prompts.md` records the assignment prompts.
- `output/audit_trail.json` starts as an empty JSON array. The backend appends privacy-minimized turn and tool events and retains earlier entries across restarts. It does not record message text, replies, names, emails, credentials, image paths, or raw errors. Review generated operational records before publishing updates.

## Project layout

```text
hw4/
  AI_prompts.md
  README.md
  requirements.txt
  .env.example
  .gitignore
  frontend/                    # React + Vite + TypeScript
  backend/
    main.py                    # FastAPI entry point
    agent.py                   # PydanticAI wiring and chat loop
    models.py                  # Shared Pydantic contracts
    tools.py                   # Read-only catalogue and inventory tools
    auth.py                    # Account/session support
    history.py                 # Signed-in chat persistence
    audit.py                   # Append-only, privacy-minimized audit
    prompts/prompt.md           # Handsome Dan system prompt
  output/
    harness.md
    design.md
    usability.md
    app_check.html
    app_check_images/
    audit_trail.json
```

The PydanticAI agent itself is organized into the four requested files: `backend/agent.py`, `backend/models.py`, `backend/tools.py`, and `backend/prompts/prompt.md`. `main.py` is the FastAPI server entry point; the additional `auth.py`, `history.py`, and `audit.py` modules support the requested account memory and audit features.

## Data and safety notes

Catalogue and inventory agent tools open SQLite read-only and cannot query account/session tables. Signup, login, session management, and account chat history use separate backend code. Product images are served only from the supplied `data/products/` directory; image files and paths are not generated by the model. Database-backed price and stock answers distinguish zero stock from a missing inventory record.

Local development uses HTTP on loopback. Before any real deployment, configure HTTPS, secure cookies, trusted origins, and shared rate/concurrency storage. Checkout, orders, password reset, and production deployment are not implemented.
