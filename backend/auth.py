"""Password verification and opaque, revocable cookie sessions.

Keep this module separate from future agent tools: passwords, hashes and session
tokens are authentication inputs only, never chatbot context.
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator, model_validator
from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD_METHOD = "scrypt:32768:8:3"
SESSION_SECONDS = 7 * 24 * 60 * 60
COOKIE_NAME = "campus_session"
PUBLIC_COLUMNS = "id, name, first_name, last_name, email, created_at"
# Makes unknown-account verification perform the same expensive hash operation.
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32), method=PASSWORD_METHOD)


class PublicUser(BaseModel):
    id: int
    name: str
    first_name: str | None
    last_name: str | None
    email: str
    created_at: str


class LoginInput(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class SignupInput(LoginInput):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    password: SecretStr = Field(min_length=12, max_length=128)
    confirm_password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def matching_passwords(self):
        if self.password.get_secret_value() != self.confirm_password.get_secret_value():
            raise ValueError("Passwords must match")
        return self


@contextmanager
def connection(database: Path):
    db = sqlite3.connect(database.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize_auth(database: Path):
    with connection(database) as db:
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_normalized ON users(lower(trim(email)))")
        db.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS auth_sessions_expiry ON auth_sessions(expires_at)")
        db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (int(time.time()),))


def verify_password(stored_hash: str, password: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        # Supplied seed format: algorithm$salt$hex_digest (120,000 iterations).
        check_password_hash(DUMMY_HASH, password)
        try:
            _, salt, digest = stored_hash.split("$")
            candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
            return hmac.compare_digest(candidate, digest)
        except (ValueError, TypeError):
            return False
    if stored_hash.startswith(PASSWORD_METHOD + "$"):
        try:
            return check_password_hash(stored_hash, password)
        except (ValueError, TypeError):
            return False
    check_password_hash(DUMMY_HASH, password)
    return False


class AttemptLimiter:
    """Small single-process development limit, using the direct client's IP."""

    def __init__(self):
        self.attempts = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, request: Request):
        now = time.monotonic()
        ip = request.client.host if request.client else "unknown"
        with self.lock:
            for key in list(self.attempts):
                times = self.attempts[key]
                while times and times[0] <= now - 600:
                    times.popleft()
                if not times:
                    del self.attempts[key]
            attempts = self.attempts[ip]
            if len(attempts) >= 30:
                raise HTTPException(429, "Too many attempts. Please wait 10 minutes and try again.", headers={"Retry-After": "600"})
            attempts.append(now)


def protect_mutation(request: Request):
    origins = {origin.strip().rstrip('/') for origin in os.getenv(
        "AUTH_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173"
    ).split(',')}
    if request.headers.get("origin") not in origins or request.headers.get("x-requested-with") != "CampusCustoms":
        raise HTTPException(403, "Please submit this request from the Campus Customs website.")


def session_fingerprint(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) != 43:
        return None
    return hashlib.sha256(token.encode()).hexdigest()


def authenticated_user(database: Path, request: Request) -> PublicUser:
    with connection(database) as db:
        row = db.execute(f"""SELECT {', '.join('u.' + field for field in PublicUser.model_fields)}
            FROM users u JOIN auth_sessions s ON s.user_id = u.id
            WHERE s.token_hash = ? AND s.expires_at > ?""",
            (session_fingerprint(request), int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, "Please log in to continue.")
    return PublicUser(**dict(row))


def auth_router(database: Path) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["accounts"])
    secure = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    limiter = AttemptLimiter()

    def create_session(db, user_id: int, request: Request, response: Response):
        now = int(time.time())
        db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
        previous = session_fingerprint(request)
        if previous:
            db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (previous,))
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                   (hashlib.sha256(token.encode()).hexdigest(), user_id, now, now + SESSION_SECONDS))
        response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                            secure=secure, samesite="lax", path="/api")
        response.headers["Cache-Control"] = "no-store"

    @router.post("/register", response_model=PublicUser, status_code=201,
                 dependencies=[Depends(protect_mutation), Depends(limiter.check)])
    def register(payload: SignupInput, request: Request, response: Response):
        hashed = generate_password_hash(payload.password.get_secret_value(), method=PASSWORD_METHOD, salt_length=16)
        try:
            with connection(database) as db:
                cursor = db.execute("""INSERT INTO users (name, first_name, last_name, email, password_hash)
                    VALUES (?, ?, ?, ?, ?)""", (f"{payload.first_name} {payload.last_name}",
                    payload.first_name, payload.last_name, str(payload.email).lower(), hashed))
                user_id = cursor.lastrowid
                create_session(db, user_id, request, response)
                return dict(db.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone())
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "Unable to create this account. Try logging in or use another email.") from exc

    @router.post("/login", response_model=PublicUser,
                 dependencies=[Depends(protect_mutation), Depends(limiter.check)])
    def login(payload: LoginInput, request: Request, response: Response):
        with connection(database) as db:
            user = db.execute("SELECT * FROM users WHERE lower(trim(email)) = ?", (str(payload.email).lower(),)).fetchone()
        password = payload.password.get_secret_value()
        valid = verify_password(user["password_hash"] if user else DUMMY_HASH, password)
        if not user or not valid:
            raise HTTPException(401, "Email or password is incorrect.")
        upgrade = generate_password_hash(password, method=PASSWORD_METHOD, salt_length=16) if user["password_hash"].startswith("pbkdf2_sha256$") else None
        with connection(database) as db:
            if upgrade:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (upgrade, user["id"]))
            create_session(db, user["id"], request, response)
            return {field: user[field] for field in PublicUser.model_fields}

    @router.get("/me", response_model=PublicUser)
    def me(request: Request, response: Response):
        response.headers["Cache-Control"] = "no-store"
        return authenticated_user(database, request)

    @router.post("/logout", status_code=204, dependencies=[Depends(protect_mutation)])
    def logout(request: Request, response: Response):
        with connection(database) as db:
            db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (session_fingerprint(request),))
        response.delete_cookie(COOKIE_NAME, path="/api", httponly=True, secure=secure, samesite="lax")
        response.headers["Cache-Control"] = "no-store"

    return router
