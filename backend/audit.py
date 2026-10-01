"""Append-only, privacy-minimized records for agent turns and tool calls."""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditTrail:
    """Write valid JSON-array events without retaining shopper text or identity."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._thread_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Create an empty JSON array once; existing records are never reset.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            with os.fdopen(fd, "r+b") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"[]\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        except Exception:
            # fdopen owns fd after successful construction; avoid hiding the
            # original filesystem error if initialization failed earlier.
            raise

    @staticmethod
    def new_run_id() -> str:
        return secrets.token_hex(8)

    def append(self, event: str, run_id: str, **fields: Any) -> None:
        record = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "event": event,
            "run_id": run_id,
            **fields,
        }
        encoded = json.dumps(record, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        with self._thread_lock:
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
            with os.fdopen(fd, "r+b") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                try:
                    stream.seek(0)
                    content = stream.read()
                    try:
                        parsed = json.loads(content)
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise RuntimeError("Audit trail is not valid JSON; refusing to overwrite it.") from exc
                    if not isinstance(parsed, list):
                        raise RuntimeError("Audit trail root must be a JSON array; refusing to overwrite it.")

                    trimmed = content.rstrip()
                    if not trimmed.endswith(b"]"):
                        raise RuntimeError("Audit trail has no closing array bracket; refusing to overwrite it.")
                    close_index = len(trimmed) - 1
                    trailing = content[close_index + 1 :]
                    separator = b"," if parsed else b""
                    suffix = separator + encoded + b"]" + trailing
                    stream.seek(close_index)
                    stream.write(suffix)
                    stream.flush()
                    os.fsync(stream.fileno())
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def turn_started(self, run_id: str, *, model: str, page: str) -> None:
        self.append("turn_started", run_id, model=model, page=page,
                    limits={"requests": 5, "tool_calls": 4, "total_tokens": 20000,
                            "completion_tokens": 1200, "timeout_seconds": 60})

    def tool_started(self, run_id: str, name: str, args: dict[str, Any], database: Path) -> None:
        self.append("tool_started", run_id, tool=name,
                    args=self._safe_args(name, args, database))

    def tool_completed(self, run_id: str, name: str, result: Any, database: Path) -> None:
        self.append("tool_completed", run_id, tool=name,
                    result=self._safe_result(result, database))

    def tool_failed(self, run_id: str, name: str, error: BaseException) -> None:
        self.append("tool_failed", run_id, tool=name, error_type=self._safe_exception_type(error))

    def turn_stopped(self, run_id: str, *, reason: str, requests: int = 0,
                     tool_calls: int = 0, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.append("turn_stopped", run_id, stop_reason=reason, requests=requests,
                    tool_calls=tool_calls, input_tokens=input_tokens, output_tokens=output_tokens)

    @staticmethod
    def _safe_exception_type(error: BaseException) -> str:
        name = type(error).__name__
        return name if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,59}", name) else "OtherError"

    @staticmethod
    def _known_catalogue(database: Path) -> tuple[set[str], set[str], set[str]]:
        """Return product IDs and safe search vocabulary; never read image paths."""
        uri = Path(database).resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute("SELECT product_id, name, garment_type, colors, search_tags FROM catalogue").fetchall()
            sizes = {str(row[0]) for row in db.execute("SELECT DISTINCT size FROM inventory")}
        ids: set[str] = set()
        words = {"hoodie", "hoodies", "hooded", "sweatshirt", "sweatshirts", "crewneck", "crewnecks",
                 "shirt", "shirts", "tee", "tees", "jacket", "jackets", "sweater", "sweaters",
                 "navy", "blue", "white", "gray", "grey", "black", "red", "pink", "green", "gold",
                 "purple", "yellow", "orange", "brown", "cream", "xs", "s", "m", "l", "xl", "xxl",
                 "small", "medium", "large", "extra", "size", "under", "below", "budget", "show",
                 "find", "looking", "want", "have", "with", "for", "yale", "bulldog", "college", "sport"}
        for product_id, name, garment_type, colors_json, tags_json in rows:
            ids.add(str(product_id))
            for value in (name, garment_type, colors_json, tags_json):
                if not value:
                    continue
                try:
                    parsed = json.loads(value) if value.startswith(("[", '"')) else value
                except (TypeError, json.JSONDecodeError):
                    parsed = value
                values = parsed if isinstance(parsed, list) else [parsed]
                for item in values:
                    words.update(token.lower() for token in re.findall(r"[A-Za-z0-9]+", str(item)))
        return ids, words, sizes

    @classmethod
    def _safe_args(cls, name: str, args: dict[str, Any], database: Path) -> dict[str, Any]:
        ids, vocabulary, known_sizes = cls._known_catalogue(database)
        safe: dict[str, Any] = {}
        if name == "search_products":
            raw_query = args.get("query")
            tokens = re.findall(r"[A-Za-z0-9]+", raw_query.lower()) if isinstance(raw_query, str) else []
            safe["query_terms"] = [word for word in tokens if word in vocabulary][:12]
            safe["query_terms_omitted"] = max(0, len(tokens) - len(safe["query_terms"]))
        if name in {"get_product_info", "get_stock", "get_product_details", "find_alternatives"}:
            product_id = args.get("product_id")
            safe["product_id"] = product_id if isinstance(product_id, str) and product_id in ids else "unknown"
        if "size" in args:
            size = args.get("size")
            normalized = re.sub(r"[\s_-]+", "", size.strip().upper()) if isinstance(size, str) else None
            aliases = {"EXTRASMALL": "XS", "XSMALL": "XS", "SMALL": "S", "MEDIUM": "M", "LARGE": "L",
                       "EXTRALARGE": "XL", "XLARGE": "XL", "2XL": "XXL", "XXLARGE": "XXL", "XXXL": "3XL"}
            normalized = aliases.get(normalized, normalized)
            safe["size"] = None if size is None else (normalized if normalized in known_sizes else "other")
        if "max_price" in args:
            amount = args.get("max_price")
            safe["max_price"] = round(float(amount), 2) if isinstance(amount, (int, float)) and math.isfinite(amount) and amount >= 0 else None
        if "in_stock_only" in args:
            safe["in_stock_only"] = bool(args["in_stock_only"])
        return safe

    @staticmethod
    def _safe_result(result: Any, database: Path) -> dict[str, Any]:
        # Import here to keep audit initialization independent of agent wiring.
        try:
            from .models import (AlternativeProductsResult, ProductDetailsResult,
                                 ProductInfoResult, ProductSearchResult, StockLookupResult)
        except ImportError:
            from models import (AlternativeProductsResult, ProductDetailsResult,
                                ProductInfoResult, ProductSearchResult, StockLookupResult)

        ids, _, known_sizes = AuditTrail._known_catalogue(database)
        safe_id = lambda value: value if isinstance(value, str) and value in ids else "unknown"
        safe_size = lambda value: value if isinstance(value, str) and value in known_sizes else None
        if isinstance(result, ProductSearchResult):
            summary = {"match_count": result.total_matches,
                       "product_ids": [safe_id(item.product_id) for item in result.products]}
            if isinstance(result, AlternativeProductsResult):
                summary.update(source_product_id=safe_id(result.source_product_id), source_found=result.source_found)
            return summary
        if isinstance(result, ProductDetailsResult):
            info = result.info
            stock = result.stock
            return {"product_id": safe_id(info.product_id), "found": info.found,
                    "price_usd": info.product.price if info.product else None,
                    "stock_status": stock.status,
                    "requested_size": safe_size(stock.requested_size),
                    "sizes": [{"size": row.size, "quantity": row.quantity} for row in stock.sizes]}
        if isinstance(result, ProductInfoResult):
            return {"product_id": safe_id(result.product_id), "found": result.found,
                    "price_usd": result.product.price if result.product else None}
        if isinstance(result, StockLookupResult):
            return {"product_id": safe_id(result.product_id), "status": result.status,
                    "size": safe_size(result.requested_size),
                    "sizes": [{"size": row.size, "quantity": row.quantity} for row in result.sizes]}
        return {"result_type": "unrecognized"}
