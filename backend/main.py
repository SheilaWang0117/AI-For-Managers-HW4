"""Run from backend/: ../.venv/bin/uvicorn main:app --reload --port 8000."""

import hashlib
import os
import re
import secrets

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Support both `uvicorn main:app` in backend/ and `uvicorn backend.main:app`
# in the homework folder, without changing sys.path or the current directory.
if __package__:
    from .audit import AuditTrail
    from .agent import ChatBusy, ChatUnavailable, ShopChat
    from .auth import PublicUser, authenticated_user, auth_router, initialize_auth, protect_mutation, COOKIE_NAME
    from .models import CustomerContext, ChatHistory, ChatReply, ChatRequest, ProductCard
    from .tools import read_products
else:
    from audit import AuditTrail
    from agent import ChatBusy, ChatUnavailable, ShopChat
    from auth import PublicUser, authenticated_user, auth_router, initialize_auth, protect_mutation, COOKIE_NAME
    from models import CustomerContext, ChatHistory, ChatReply, ChatRequest, ProductCard
    from tools import read_products

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATABASE = DATA_DIR / "campus_customs.db"
AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
PROJECT_ENV = Path(__file__).resolve().parents[1] / ".env"
WORKSPACE_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(PROJECT_ENV, override=False)
load_dotenv(WORKSPACE_ENV, override=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_auth(DATABASE)
    app.state.shop_chat = ShopChat(DATABASE, audit=AuditTrail(AUDIT_PATH))
    try:
        yield
    finally:
        await app.state.shop_chat.close()


app = FastAPI(title="Campus Customs", version="0.4.0", lifespan=lifespan)
app.include_router(auth_router(DATABASE))


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Never echo submitted values (especially passwords) in validation errors.
    detail = "Please enter a message of 1–1,000 characters and a valid page context." if request.url.path == "/api/chat" else "Please check the form fields and password requirements."
    return JSONResponse(status_code=422, content={"detail": detail}, headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith(("/api/auth/", "/api/chat")):
        response.headers["Cache-Control"] = "no-store"
    return response


def optional_user(request: Request) -> PublicUser | None:
    # An expired/invalid login is not silently treated as a guest request.
    if request.cookies.get(COOKIE_NAME):
        return authenticated_user(DATABASE, request)
    return None


def guest_key(request: Request, response: Response) -> str:
    token = request.cookies.get("campus_guest", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        token = secrets.token_urlsafe(32)
        response.set_cookie("campus_guest", token, httponly=True, samesite="lax", path="/api",
                            secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true")
    return "guest:" + hashlib.sha256(token.encode()).hexdigest()


@app.get("/api/products", response_model=list[ProductCard])
def products():
    return read_products(DATABASE)


@app.get("/api/products/{product_id}", response_model=ProductCard)
def product(product_id: str):
    matches = read_products(DATABASE, product_id)
    if not matches:
        raise HTTPException(404, "Product not found")
    return matches[0]


@app.post("/api/chat", response_model=ChatReply, dependencies=[Depends(protect_mutation)])
async def chat(payload: ChatRequest, request: Request, response: Response, user: PublicUser | None = Depends(optional_user)):
    try:
        if payload.page_context.product_id and not read_products(DATABASE, payload.page_context.product_id):
            raise HTTPException(404, "This product page is no longer in the catalogue. Please open another item.")
        customer = CustomerContext(name=user.name, first_name=user.first_name, email=user.email) if user else None
        key = f"user:{user.id}" if user else guest_key(request, response)
        ip = request.client.host if request.client else "unknown"
        return await request.app.state.shop_chat.reply(key, user.id if user else None, payload.message,
                                                       customer=customer, page_context=payload.page_context,
                                                       rate_key=f"guest-ip:{ip}")
    except ChatBusy as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": str(exc.retry_after)}) from None
    except ChatUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


@app.get("/api/chat/history", response_model=ChatHistory)
async def chat_history(request: Request, response: Response, user: PublicUser | None = Depends(optional_user)):
    try:
        key = f"user:{user.id}" if user else guest_key(request, response)
        return ChatHistory(messages=request.app.state.shop_chat.history(key, user.id if user else None))
    except ChatBusy as exc:
        raise HTTPException(429, str(exc)) from None


# Expose only product images, never the database or other data-directory files.
app.mount("/api/images", StaticFiles(directory=DATA_DIR / "products"), name="images")
