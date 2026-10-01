"""Deterministic local tests. FunctionModel never contacts an AI provider."""

import asyncio
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from backend import main
from backend.agent import ChatBusy, ChatUnavailable, HISTORY_TTL, ShopChat, build_agent
from backend.auth import COOKIE_NAME, initialize_auth
from backend.history import initialize_history, load_history, save_turn
from backend.models import CustomerContext, PageContext, ChatMessage, ChatRequest, ProductInfoResult, SizeStock, StockLookupResult
from backend.tools import ShopDependencies, catalogue_only, get_product_info, get_stock, get_product_details, find_alternatives, matching_products, read_products, search_products


def local_model(messages, info):
    if any(part.part_kind == "tool-return" for part in messages[-1].parts):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
            {"reply": "The navy hoodie is $42.00, with 3 available in M.", "product_ids": ["navy-hoodie"]})])
    return ModelResponse(parts=[ToolCallPart("search_products", {"query": "navy hoodies", "max_price": 50,
                                                               "size": "M", "in_stock_only": True})])


class ChatTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "campus_customs.db"
        with closing(sqlite3.connect(self.database)) as db, db:
            db.executescript("""
                CREATE TABLE catalogue (product_id TEXT PRIMARY KEY, name TEXT, garment_type TEXT,
                    description TEXT, colors TEXT, search_tags TEXT, image_file_path TEXT, price REAL);
                CREATE TABLE inventory (id INTEGER PRIMARY KEY, product_id TEXT, size TEXT, quantity INTEGER);
                CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password_hash TEXT,
                    first_name TEXT, last_name TEXT, created_at TEXT DEFAULT (datetime('now')));
                INSERT INTO catalogue VALUES ('navy-hoodie','Navy Hoodie','hoodie','A navy campus hoodie.',
                    '["navy"]','["Yale"]','products/navy.jpg',42.0);
                INSERT INTO inventory VALUES (1,'navy-hoodie','M',3),(2,'navy-hoodie','S',0);
                INSERT INTO users (id,name,email,password_hash) VALUES (1,'Test','test@example.com','do-not-share');
            """)
        initialize_auth(self.database)
        self.agent = build_agent(FunctionModel(local_model))
        self.service = ShopChat(self.database, agent=self.agent)

    async def test_agent_calls_catalogue_tool_and_hydrates_typed_cards(self):
        reply = await self.service.reply("session-a", 1, "Find a navy hoodie under $50 in M.")
        self.assertIn("$42.00", reply.reply)
        self.assertEqual(reply.products[0].product_id, "navy-hoodie")
        self.assertEqual(reply.products[0].price, 42)
        self.assertEqual(reply.products[0].inventory[1].quantity, 3)
        self.assertEqual(reply.search.total_matches, 1)
        self.assertEqual(reply.search.products, reply.products)
        self.assertEqual(self.service.history("session-a", 1)[-1].search, reply.search)
        self.assertEqual(len(self.service.history("session-a", 1)), 2)
        self.assertEqual(self.service.history("session-b", 2), [])

    async def test_unknown_product_ids_are_rejected_without_fake_reply(self):
        def invent(messages, info):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
                                 {"reply": "Try this made-up product.", "product_ids": ["not-real"]})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(invent)))
        with self.assertRaises(ChatUnavailable):
            await service.reply("session", 1, "Show a product")
        self.assertEqual(service.history("session", 1), [])
        self.assertFalse(service.conversation("user:1").busy)
        self.assertEqual(service.active, 0)

    async def test_provider_failure_is_sanitized_and_history_is_unchanged(self):
        def failing(messages, info):
            raise RuntimeError("PRIVATE_PROVIDER_DETAIL")
        service = ShopChat(self.database, agent=build_agent(FunctionModel(failing)))
        with self.assertLogs("backend.agent", level="WARNING") as logs:
            with self.assertRaises(ChatUnavailable) as error:
                await service.reply("session", 1, "Hello")
        self.assertNotIn("PRIVATE_PROVIDER_DETAIL", str(error.exception))
        self.assertNotIn("PRIVATE_PROVIDER_DETAIL", " ".join(logs.output))
        self.assertEqual(service.history("session", 1), [])

    async def test_history_limits_expiry_and_concurrent_send_guard(self):
        for _ in range(7):
            await self.service.reply("session", None, "Find a hoodie")
        conversation = self.service.conversation("session")
        self.assertEqual(len(conversation.messages), 12)
        conversation.busy = True
        with self.assertRaises(ChatBusy):
            await self.service.reply("session", None, "Another message")
        conversation.busy = False
        conversation.touched -= HISTORY_TTL + 1
        self.assertEqual(self.service.conversation("session").messages, [])
        other = ShopChat(self.database, agent=self.agent)
        for _ in range(15):
            other.check_rate(5)
        with self.assertRaises(ChatBusy):
            other.check_rate(5)

    async def test_catalogue_queries_cannot_read_credentials_or_invent_stock(self):
        self.assertEqual(len(matching_products(self.database, "navy hoodies", 50, "M", True)), 1)
        self.assertEqual(matching_products(self.database, "navy hoodies", 50, "S", True), [])
        self.assertEqual(matching_products(self.database, "navy", 20), [])
        self.assertEqual(read_products(self.database, "' OR 1=1 --"), [])
        with closing(sqlite3.connect(self.database)) as db:
            db.set_authorizer(catalogue_only)
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("SELECT password_hash FROM users").fetchall()
        for invalid in ("  ", "x" * 1001):
            with self.assertRaises(ValueError):
                ChatRequest(message=invalid)

    async def test_api_supports_guests_and_requires_origin_then_returns_account_reply(self):
        import hashlib
        import secrets
        import time
        token = secrets.token_urlsafe(32)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("INSERT INTO auth_sessions VALUES (?,?,?,?)",
                       (hashlib.sha256(token.encode()).hexdigest(), 1, int(time.time()), int(time.time()) + 300))
        headers = {"Origin": "http://127.0.0.1:5173", "X-Requested-With": "CampusCustoms"}
        with patch.object(main, "DATABASE", self.database), TestClient(main.app) as client:
            main.app.state.shop_chat = self.service
            self.assertEqual(client.post("/api/chat", json={"message": "Hi"}, headers=headers).status_code, 200)
            self.assertEqual(len(client.get("/api/chat/history").json()["messages"]), 2)
            client.cookies.set(COOKIE_NAME, token)
            self.assertEqual(client.post("/api/chat", json={"message": "Hi"}).status_code, 403)
            response = client.post("/api/chat", json={"message": "Find a navy hoodie"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.json()["products"][0]["price"], 42)
            self.assertEqual(response.json()["search"]["total_matches"], 1)
            history = client.get("/api/chat/history").json()["messages"]
            self.assertEqual([item["role"] for item in history], ["user", "assistant"])
            self.assertEqual(history[-1]["search"], response.json()["search"])
            self.assertEqual(client.post("/api/chat", json={"message": "Hi", "user_id": 2}, headers=headers).status_code, 422)
            self.assertNotIn("password_hash", response.text)

    async def test_search_counts_all_matches_but_returns_six_database_cards(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            for number in range(8):
                db.execute("INSERT INTO catalogue SELECT ?, name, garment_type, description, colors, search_tags, image_file_path, ? FROM catalogue WHERE product_id='navy-hoodie'",
                           (f"hoodie-{number}", 50 + number))
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        result = search_products(ctx, "hoodies")
        self.assertEqual(result.total_matches, 9)
        self.assertEqual(len(result.products), 6)
        self.assertEqual([p.price for p in result.products], [42, 50, 51, 52, 53, 54])
        self.assertEqual(set(ctx.deps.seen_products), {p.product_id for p in result.products})
        self.assertIs(ctx.deps.last_search, result)
        filtered = search_products(ctx, "hoodies", max_price=45, size="medium", in_stock_only=True)
        self.assertEqual((filtered.total_matches, filtered.size, filtered.max_price), (1, "M", 45))
        empty = search_products(ctx, "spacesuit")
        self.assertEqual((empty.total_matches, empty.products), (0, []))
        self.assertIs(ctx.deps.last_search, empty)

    async def test_no_search_and_empty_search_have_different_api_results(self):
        def greeting(messages, info):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reply": "Hello from Handsome Dan!", "product_ids": []})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(greeting)))
        self.assertIsNone((await service.reply("test", 1, "Hello")).search)

        def no_matches(messages, info):
            if not any(part.part_kind == "tool-return" for part in messages[-1].parts):
                return ModelResponse(parts=[ToolCallPart("search_products", {"query": "spacesuit"})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reply": "No matches in the catalogue.", "product_ids": []})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(no_matches)))
        reply = await service.reply("test", 1, "Spacesuits?")
        self.assertEqual(reply.search.total_matches, 0)
        self.assertEqual(reply.search.products, [])

    async def test_product_info_uses_exact_catalogue_values_and_missing_is_null(self):
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        result = get_product_info(ctx, "navy-hoodie")
        self.assertTrue(result.found)
        self.assertEqual(result.product.price, 42)
        self.assertEqual(result.product.description, "A navy campus hoodie.")
        self.assertEqual(result.product.currency, "USD")
        missing = get_product_info(ctx, "not-a-product")
        self.assertFalse(missing.found)
        self.assertIsNone(missing.product)
        self.assertEqual(ctx.deps.tool_names, ["get_product_info", "get_product_info"])

    async def test_size_stock_distinguishes_sold_out_unlisted_and_missing_product(self):
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        available = get_stock(ctx, "navy-hoodie", " medium ")
        self.assertEqual((available.requested_size, available.status, available.quantity), ("M", "in_stock", 3))
        self.assertEqual(len(available.sizes), 1)
        sold_out = get_stock(ctx, "navy-hoodie", "small")
        self.assertEqual((sold_out.status, sold_out.quantity), ("out_of_stock", 0))
        missing_size = get_stock(ctx, "navy-hoodie", "3XL")
        self.assertEqual(missing_size.status, "size_not_found")
        self.assertIsNone(missing_size.quantity)
        self.assertEqual(missing_size.sizes, [])
        missing_product = get_stock(ctx, "' OR 1=1 --", "M")
        self.assertEqual(missing_product.status, "product_not_found")
        self.assertIsNone(missing_product.quantity)

    async def test_stock_total_no_inventory_and_fresh_database_reads(self):
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        overview = get_stock(ctx, "navy-hoodie")
        self.assertIsNone(overview.requested_size)
        self.assertEqual(overview.quantity, 3)
        self.assertEqual([(row.size, row.quantity) for row in overview.sizes], [("S", 0), ("M", 3)])
        get_product_info(ctx, "navy-hoodie")
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE catalogue SET price=47.5 WHERE product_id='navy-hoodie'")
            db.execute("UPDATE inventory SET quantity=0 WHERE product_id='navy-hoodie' AND size='M'")
        self.assertEqual(get_product_info(ctx, "navy-hoodie").product.price, 47.5)
        self.assertEqual(get_stock(ctx, "navy-hoodie", "M").status, "out_of_stock")
        self.assertEqual(get_stock(ctx, "navy-hoodie").quantity, 0)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("DELETE FROM inventory")
        unknown = get_stock(ctx, "navy-hoodie", "M")
        self.assertEqual(unknown.status, "no_inventory")
        self.assertIsNone(unknown.quantity)

    async def test_lookup_models_reject_contradictory_stock(self):
        with self.assertRaises(ValueError):
            SizeStock(size="M", quantity=0, status="in_stock")
        with self.assertRaises(ValueError):
            StockLookupResult(product_id="navy-hoodie", status="size_not_found", quantity=0)
        with self.assertRaises(ValueError):
            StockLookupResult(product_id="navy-hoodie", requested_size="M", status="in_stock", quantity=3,
                              sizes=[SizeStock(size="S", quantity=3, status="in_stock")])
        with self.assertRaises(ValueError):
            ProductInfoResult(product_id="navy-hoodie", found=True)

    async def test_agent_can_call_both_dedicated_tools(self):
        def lookup_model(messages, info):
            returns = [part.tool_name for message in messages for part in message.parts if part.part_kind == "tool-return"]
            if "get_product_info" not in returns:
                return ModelResponse(parts=[ToolCallPart("get_product_info", {"product_id": "navy-hoodie"})])
            if "get_stock" not in returns:
                return ModelResponse(parts=[ToolCallPart("get_stock", {"product_id": "navy-hoodie", "size": "S"})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
                {"reply": "The navy hoodie is $42.00. Size S is out of stock (0 available).", "product_ids": ["navy-hoodie"]})])
        deps = ShopDependencies(self.database)
        result = await build_agent(FunctionModel(lookup_model)).run("Price and stock for S?", deps=deps)
        self.assertEqual(deps.tool_names, ["get_product_info", "get_stock"])
        self.assertEqual(deps.lookup_results[-1].status, "out_of_stock")
        self.assertIn("out of stock", result.output.reply)
        self.assertEqual(result.output.product_ids, ["navy-hoodie"])

    async def test_agent_rejects_claiming_unlisted_size_is_unavailable(self):
        def unsupported_claim(messages, info):
            if not any(part.part_kind == "tool-return" for message in messages for part in message.parts):
                return ModelResponse(parts=[ToolCallPart("get_stock", {"product_id": "navy-hoodie", "size": "3XL"})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
                {"reply": "3XL is not available.", "product_ids": ["navy-hoodie"]})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(unsupported_claim)))
        with self.assertRaises(ChatUnavailable):
            await service.reply("test", 1, "Is 3XL available?")
        self.assertEqual(service.history("test", 1), [])

    async def test_account_memory_survives_new_service_and_session_without_guest_writes(self):
        page = PageContext(page="product", product_id="navy-hoodie")
        await self.service.reply("first-login", 1, "My favorite color is navy.", page_context=page)
        before = load_history(self.database, 1)
        restarted = ShopChat(self.database, agent=self.agent)
        self.assertEqual(restarted.history("new-login", 1), before)
        self.assertEqual(before[0].page_context, page)
        self.assertIsNotNone(before[1].search)
        self.assertEqual(restarted.history("new-login", 2), [])
        await restarted.reply("guest-a", None, "Guest question")
        self.assertEqual(load_history(self.database, 1), before)
        self.assertEqual(len(restarted.history("guest-a", None)), 2)
        self.assertEqual(restarted.history("guest-b", None), [])
        self.assertEqual(ShopChat(self.database, agent=self.agent).history("guest-a", None), [])

    async def test_account_guard_is_shared_across_logins_and_model_history_is_bounded(self):
        for index in range(8):
            save_turn(self.database, 1, [ChatMessage(role="user", content=f"Preference {index}"),
                                         ChatMessage(role="assistant", content="Noted.")])
        def inspect_history(messages, info):
            prior = [p.content for m in messages for p in m.parts if p.part_kind == "user-prompt"]
            self.assertNotIn("Preference 0", prior)
            self.assertIn("Preference 7", prior)
            self.assertEqual(len(prior), 7)  # Six previous turns and current message.
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reply": "Welcome back!", "product_ids": []})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(inspect_history)))
        await service.reply("another-login", 1, "Hello")
        self.assertEqual(len(service.history("any-login", 1)), 18)
        service.conversation("user:1").busy = True
        with self.assertRaises(ChatBusy):
            await service.reply("different-login", 1, "Hello again")

    async def test_legacy_migration_preserves_content_and_failed_save_is_atomic(self):
        # Recreate exactly the supplied pre-P8 table shape in this disposable database.
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("DROP TABLE chat_messages")
            db.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), role TEXT NOT NULL, content TEXT NOT NULL, products_json TEXT, created_at TEXT DEFAULT (datetime('now')))")
            db.execute("INSERT INTO chat_messages(user_id,role,content,products_json) VALUES (1,'assistant','Legacy message','invalid old metadata')")
        initialize_history(self.database)
        initialize_history(self.database)
        self.assertEqual(load_history(self.database, 1)[0].content, "Legacy message")
        self.assertEqual(load_history(self.database, 1)[0].products, [])
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("CREATE TRIGGER fail_assistant BEFORE INSERT ON chat_messages WHEN NEW.role='assistant' BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(ChatUnavailable):
            await self.service.reply("session", 1, "Find a hoodie")
        self.assertEqual(len(load_history(self.database, 1)), 1)

    async def test_api_identity_page_validation_and_account_isolation(self):
        import hashlib
        import secrets
        import time
        tokens = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("INSERT INTO users(id,name,first_name,email,password_hash) VALUES(2,'Other Shopper','Other','other@example.com','SECRET-HASH')")
            for user_id, token in enumerate(tokens, start=1):
                db.execute("INSERT INTO auth_sessions VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, int(time.time()), int(time.time()) + 300))
        contexts = []
        def inspect(messages, info):
            contexts.append(info.instructions)
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reply": "Hello, shopper!", "product_ids": []})])
        headers = {"Origin": "http://127.0.0.1:5173", "X-Requested-With": "CampusCustoms"}
        with patch.object(main, "DATABASE", self.database), TestClient(main.app) as client:
            main.app.state.shop_chat = ShopChat(self.database, agent=build_agent(FunctionModel(inspect)))
            client.cookies.set(COOKIE_NAME, tokens[0])
            payload = {"message": "This in pink?", "page_context": {"page": "product", "product_id": "navy-hoodie"}}
            self.assertEqual(client.post("/api/chat", json=payload, headers=headers).status_code, 200)
            self.assertIn('"email": "test@example.com"', contexts[-1])
            self.assertIn('"product_name": "Navy Hoodie"', contexts[-1])
            self.assertNotIn(tokens[0], contexts[-1])
            self.assertNotIn('do-not-share', contexts[-1])
            self.assertNotIn('created_at', contexts[-1])
            for extra in ({"user_id": 2}, {"customer": {"email": "other@example.com"}}):
                self.assertEqual(client.post("/api/chat", json={**payload, **extra}, headers=headers).status_code, 422)
            for page in ({"page": "product"}, {"page": "home", "product_id": "navy-hoodie"},
                         {"page": "product", "product_id": "navy-hoodie", "price": 0}):
                self.assertEqual(client.post("/api/chat", json={**payload, "page_context": page}, headers=headers).status_code, 422)
            self.assertEqual(client.post("/api/chat", json={**payload, "page_context": {"page": "product", "product_id": "unknown"}}, headers=headers).status_code, 404)
            client.cookies.set(COOKIE_NAME, tokens[1])
            self.assertEqual(client.get("/api/chat/history?user_id=1").json()["messages"], [])
            self.assertEqual(client.post("/api/chat", json={"message": "Hello"}, headers=headers).status_code, 200)
            self.assertIn('"email": "other@example.com"', contexts[-1])
            self.assertIn('"page": "other"', contexts[-1])
            self.assertNotIn('navy-hoodie', contexts[-1])
            client.cookies.set(COOKIE_NAME, "expired-or-invalid")
            self.assertEqual(client.get("/api/chat/history").status_code, 401)
            self.assertEqual(client.post("/api/chat", json=payload, headers=headers).status_code, 401)
            client.cookies.clear()
            self.assertEqual(client.get("/api/chat/history").json()["messages"], [])
            cookie = client.get("/api/chat/history").headers.get("set-cookie")
            self.assertIsNone(cookie)  # Existing guest cookie is reused.
            self.assertEqual(client.post("/api/chat", json={"message": "Guest hello"}, headers=headers).status_code, 200)
            self.assertIn('"customer": null', contexts[-1])
            self.assertEqual(len(load_history(self.database, 1)), 2)
            self.assertEqual(len(load_history(self.database, 2)), 2)

    async def test_guest_rate_limit_is_per_ip_not_per_cookie(self):
        def greeting(messages, info):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reply": "Hello, guest!", "product_ids": []})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(greeting)))
        for index in range(15):
            await service.reply(f"guest-{index}", None, "Hello", rate_key="guest-ip:test")
        with self.assertRaises(ChatBusy):
            await service.reply("new-cookie", None, "Hello", rate_key="guest-ip:test")
        self.assertEqual(load_history(self.database, 1), [])

    async def test_context_changes_between_runs_and_current_page_requires_tool_lookup(self):
        observed = []
        def contextual_model(messages, info):
            observed.append(info.instructions)
            if not any(p.part_kind == "tool-return" for p in messages[-1].parts):
                return ModelResponse(parts=[ToolCallPart("get_product_info", {"product_id": "navy-hoodie"})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name,
                {"reply": "This hoodie lists navy. Pink is not listed.", "product_ids": ["navy-hoodie"]})])
        customer = CustomerContext(name="Test Shopper", first_name="Test", email="test@example.com")
        agent = build_agent(FunctionModel(contextual_model))
        deps = ShopDependencies(self.database, customer=customer,
                                page_context=PageContext(page="product", product_id="navy-hoodie"),
                                current_product=read_products(self.database, "navy-hoodie")[0])
        await agent.run("This in pink?", deps=deps)
        self.assertEqual(deps.tool_names, ["get_product_info"])
        self.assertIn('"product_name": "Navy Hoodie"', observed[0])
        # A new run must not retain the preceding customer's profile or page.
        await agent.run("Find the navy hoodie", deps=ShopDependencies(self.database))
        self.assertIn('"customer": null', observed[-1])
        self.assertIn('"page": "other"', observed[-1])
        self.assertNotIn('test@example.com', observed[-1])

    async def test_combined_details_reads_once_and_preserves_unknown_stock(self):
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        with patch('backend.tools.read_products', wraps=read_products) as read:
            result = get_product_details(ctx, 'navy-hoodie', 'medium')
            self.assertEqual(read.call_count, 1)
        self.assertEqual(result.info.product.price, 42)
        self.assertEqual((result.stock.requested_size, result.stock.quantity), ('M', 3))
        self.assertEqual(ctx.deps.tool_names, ['get_product_details'])
        self.assertEqual(ctx.deps.lookup_results, [result.info, result.stock])
        self.assertEqual(get_product_details(ctx, 'navy-hoodie', 'small').stock.status, 'out_of_stock')
        self.assertIsNone(get_product_details(ctx, 'navy-hoodie', '3XL').stock.quantity)
        missing = get_product_details(ctx, 'missing', 'M')
        self.assertFalse(missing.info.found)
        self.assertEqual(missing.stock.status, 'product_not_found')
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE catalogue SET price=44 WHERE product_id='navy-hoodie'")
            db.execute("UPDATE inventory SET quantity=7 WHERE size='M'")
        fresh = get_product_details(ctx, 'navy-hoodie', 'M')
        self.assertEqual((fresh.info.product.price, fresh.stock.quantity), (44, 7))

    async def test_alternatives_respect_family_size_budget_and_exclude_source(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            for pid, category, price, quantity in [
                ('close-hood', 'hooded sweatshirt', 43, 2), ('cheap-hood', 'pullover hoodie', 30, 4),
                ('sold-hood', 'hoodie', 41, 0), ('expensive-hood', 'hoodie', 80, 5),
                ('wrong-family', 'crewneck sweatshirt', 42, 6), ('no-inventory', 'hoodie', 42, None),
            ]:
                db.execute("INSERT INTO catalogue SELECT ?, ?, ?, description, colors, search_tags, image_file_path, ? FROM catalogue WHERE product_id='navy-hoodie'", (pid, pid, category, price))
                if quantity is not None:
                    db.execute("INSERT INTO inventory(product_id,size,quantity) VALUES(?, 'M', ?)", (pid, quantity))
        ctx = SimpleNamespace(deps=ShopDependencies(self.database))
        result = find_alternatives(ctx, 'navy-hoodie', 'medium', 50)
        self.assertEqual([p.product_id for p in result.products], ['close-hood', 'cheap-hood'])
        self.assertEqual((result.total_matches, result.size, result.matching_category), (2, 'M', 'hoodies'))
        self.assertEqual(ctx.deps.last_search.products, result.products)
        self.assertEqual(set(ctx.deps.seen_products), {'close-hood', 'cheap-hood'})
        empty = find_alternatives(ctx, 'navy-hoodie', 'M', 20)
        self.assertTrue(empty.source_found)
        self.assertEqual(empty.products, [])
        self.assertEqual(ctx.deps.last_search.total_matches, 0)
        self.assertEqual(find_alternatives(ctx, 'navy-hoodie', '3XL').products, [])
        missing = find_alternatives(ctx, 'unknown', 'M')
        self.assertFalse(missing.source_found)
        self.assertIsNone(missing.matching_category)

    async def test_combined_tool_can_answer_in_two_model_requests(self):
        def combined(messages, info):
            if not any(p.part_kind == 'tool-return' for p in messages[-1].parts):
                return ModelResponse(parts=[ToolCallPart('get_product_details', {'product_id': 'navy-hoodie', 'size': 'M'})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {'reply': 'It is $42.00, with 3 in M.', 'product_ids': ['navy-hoodie']})])
        deps = ShopDependencies(self.database)
        result = await build_agent(FunctionModel(combined)).run('Price and M stock?', deps=deps)
        self.assertEqual(deps.tool_names, ['get_product_details'])
        self.assertEqual(result.usage.requests, 2)

    async def test_agent_rejects_original_item_as_an_alternative(self):
        def wrong_pick(messages, info):
            returns = [p.tool_name for m in messages for p in m.parts if p.part_kind == 'tool-return']
            if 'get_product_details' not in returns:
                return ModelResponse(parts=[ToolCallPart('get_product_details', {'product_id': 'navy-hoodie', 'size': 'S'})])
            if 'find_alternatives' not in returns:
                return ModelResponse(parts=[ToolCallPart('find_alternatives', {'product_id': 'navy-hoodie', 'size': 'S'})])
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {'reply': 'Try this alternative.', 'product_ids': ['navy-hoodie']})])
        service = ShopChat(self.database, agent=build_agent(FunctionModel(wrong_pick)))
        with self.assertRaises(ChatUnavailable):
            await service.reply('test', 1, 'Any alternatives in S?')
        self.assertEqual(load_history(self.database, 1), [])


if __name__ == "__main__":
    unittest.main()
