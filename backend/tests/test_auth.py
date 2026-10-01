import hashlib
import secrets
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from backend.auth import COOKIE_NAME, PASSWORD_METHOD, auth_router, initialize_auth
from backend.main import invalid_request


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "accounts.db"
        self.password = secrets.token_urlsafe(24)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                first_name TEXT, last_name TEXT)""")
            salt = "development-salt"
            digest = hashlib.pbkdf2_hmac("sha256", b"legacy-fixture-password", salt.encode(), 120_000).hex()
            db.execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)",
                       ("Seed Bulldog", "legacy@example.test", f"pbkdf2_sha256${salt}${digest}"))
        initialize_auth(self.database)
        self.app = FastAPI()
        self.app.add_exception_handler(RequestValidationError, invalid_request)
        self.app.include_router(auth_router(self.database))
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.headers = {"Origin": "http://127.0.0.1:5173", "X-Requested-With": "CampusCustoms"}

    def signup(self, **overrides):
        return dict(first_name="New", last_name="Bulldog", email="new@example.com",
                    password=self.password, confirm_password=self.password, **overrides)

    def post(self, route, data):
        return self.client.post("/api/auth/" + route, json=data, headers=self.headers)

    def test_registration_hash_cookie_reload_and_revocation(self):
        response = self.post("register", self.signup())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {"id", "name", "first_name", "last_name", "email", "created_at"})
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Path=/api", cookie)
        token = self.client.cookies.get(COOKIE_NAME)
        with closing(sqlite3.connect(self.database)) as db, db:
            hashed = db.execute("SELECT password_hash FROM users WHERE email='new@example.com'").fetchone()[0]
            stored_token = db.execute("SELECT token_hash FROM auth_sessions").fetchone()[0]
        self.assertTrue(hashed.startswith(PASSWORD_METHOD + "$"))
        self.assertNotIn(self.password, hashed)
        self.assertNotEqual(stored_token, token)
        self.assertEqual(stored_token, hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(self.client.get("/api/auth/me").json()["email"], "new@example.com")
        # A new HTTP client using the cookie restores the persisted session.
        with TestClient(self.app) as fresh:
            fresh.cookies.set(COOKIE_NAME, token)
            self.assertEqual(fresh.get("/api/auth/me").status_code, 200)
        self.assertEqual(self.post("logout", {}).status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        with TestClient(self.app) as replay:
            replay.cookies.set(COOKIE_NAME, token)
            self.assertEqual(replay.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.post("login", {"email": "new@example.com", "password": self.password}).status_code, 200)

    def test_legacy_login_upgrades_hash_without_changing_password(self):
        response = self.post("login", {"email": " LEGACY@EXAMPLE.TEST ", "password": "legacy-fixture-password"})
        self.assertEqual(response.status_code, 200)
        with closing(sqlite3.connect(self.database)) as db, db:
            hashed = db.execute("SELECT password_hash FROM users WHERE id=1").fetchone()[0]
        self.assertTrue(hashed.startswith(PASSWORD_METHOD + "$"))
        self.post("logout", {})
        self.assertEqual(self.post("login", {"email": "legacy@example.test", "password": "legacy-fixture-password"}).status_code, 200)

    def test_validation_and_case_insensitive_duplicate(self):
        for changes in ({"confirm_password": "another-long-password"}, {"password": "short", "confirm_password": "short"}, {"first_name": "   "}, {"email": "bad-address"}, {"password": "x" * 129, "confirm_password": "x" * 129}):
            data = self.signup(); data.update(changes)
            response = self.post("register", data)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Please check the form fields and password requirements."})
        self.assertEqual(self.post("register", self.signup()).status_code, 201)
        data = self.signup(); data["email"] = " NEW@EXAMPLE.COM "
        self.assertEqual(self.post("register", data).status_code, 409)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 2)

    def test_wrong_password_and_unknown_email_have_same_error(self):
        first = self.post("login", {"email": "legacy@example.test", "password": self.password})
        second = self.post("login", {"email": "missing@example.com", "password": self.password})
        self.assertEqual(first.status_code, 401)
        self.assertEqual(first.json(), second.json())
        self.assertNotIn("password_hash", first.text)
        self.assertIsNone(self.client.cookies.get(COOKIE_NAME))

    def test_origin_header_expiry_and_token_rotation(self):
        for headers in ({}, {"Origin": "https://untrusted.example", "X-Requested-With": "CampusCustoms"}, {"Origin": "http://127.0.0.1:5173"}):
            self.assertEqual(self.client.post("/api/auth/register", json=self.signup(), headers=headers).status_code, 403)
        self.post("register", self.signup())
        previous = self.client.cookies.get(COOKIE_NAME)
        self.post("login", {"email": "new@example.com", "password": self.password})
        self.assertNotEqual(previous, self.client.cookies.get(COOKIE_NAME))
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM auth_sessions").fetchone()[0], 1)
            db.execute("UPDATE auth_sessions SET expires_at=?", (int(time.time()) - 1,))
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        with TestClient(self.app) as forged:
            forged.cookies.set(COOKIE_NAME, secrets.token_urlsafe(32))
            self.assertEqual(forged.get("/api/auth/me").status_code, 401)

    def test_attempt_limit_and_secure_cookie_configuration(self):
        for _ in range(30):
            self.assertEqual(self.post("login", {}).status_code, 422)
        blocked = self.post("login", {})
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.headers["retry-after"], "600")
        with patch.dict("os.environ", {"AUTH_COOKIE_SECURE": "true"}):
            secure_app = FastAPI()
            secure_app.include_router(auth_router(self.database))
            with TestClient(secure_app, base_url="https://testserver") as client:
                response = client.post("/api/auth/register", json=self.signup(), headers=self.headers)
                self.assertEqual(response.status_code, 201)
                self.assertIn("Secure", response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
