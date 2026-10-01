"""Account-scoped chat storage. Not exposed as an agent tool."""

import json
from pathlib import Path

from pydantic import ValidationError

if __package__:
    from .auth import connection
    from .models import ChatMessage, PageContext, ProductCard, ProductSearchResult
else:
    from auth import connection
    from models import ChatMessage, PageContext, ProductCard, ProductSearchResult

DISPLAY_MESSAGES = 100


def initialize_history(database: Path):
    with connection(database) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            products_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        columns = {row['name'] for row in db.execute('PRAGMA table_info(chat_messages)')}
        for name in ('search_json', 'page_context_json'):
            if name not in columns:
                db.execute(f'ALTER TABLE chat_messages ADD COLUMN {name} TEXT')
        db.execute('CREATE INDEX IF NOT EXISTS chat_messages_user_order ON chat_messages(user_id, id)')


def optional_model(model, value):
    if not value:
        return None
    try:
        return model.model_validate_json(value)
    except (ValueError, ValidationError):
        # Legacy malformed metadata must not hide the shopper's actual messages.
        return None


def load_history(database: Path, user_id: int, limit: int = DISPLAY_MESSAGES) -> list[ChatMessage]:
    with connection(database) as db:
        rows = db.execute('''SELECT role, content, products_json, search_json, page_context_json
            FROM chat_messages WHERE user_id = ? AND role IN ('user', 'assistant')
            ORDER BY id DESC LIMIT ?''', (user_id, limit)).fetchall()
    messages = []
    for row in reversed(rows):
        products = []
        try:
            values = json.loads(row['products_json'] or '[]')
            if isinstance(values, list):
                for value in values[:6]:
                    try:
                        products.append(ProductCard.model_validate(value))
                    except (ValueError, ValidationError):
                        continue
        except (ValueError, TypeError):
            pass
        messages.append(ChatMessage(role=row['role'], content=row['content'], products=products,
                                    search=optional_model(ProductSearchResult, row['search_json']),
                                    page_context=optional_model(PageContext, row['page_context_json'])))
    return messages


def save_turn(database: Path, user_id: int, messages: list[ChatMessage]):
    """Commit both messages together; a failed turn never leaves half a pair."""
    with connection(database) as db:
        db.executemany('''INSERT INTO chat_messages
            (user_id, role, content, products_json, search_json, page_context_json)
            VALUES (?, ?, ?, ?, ?, ?)''', [
                (user_id, item.role, item.content,
                 json.dumps([product.model_dump() for product in item.products]),
                 item.search.model_dump_json() if item.search else None,
                 item.page_context.model_dump_json() if item.page_context else None)
                for item in messages
            ])
