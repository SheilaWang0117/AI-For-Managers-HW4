"""Read-only catalogue functions. No account, session, shell, or SQL tool."""

import json
import math
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic_ai import ModelRetry, RunContext

if __package__:
    from .models import AlternativeProductsResult, ProductDetailsResult, CustomerContext, PageContext, ProductCard, ProductInfo, ProductInfoResult, ProductSearchResult, SizeStock, Stock, StockLookupResult
else:
    from models import AlternativeProductsResult, ProductDetailsResult, CustomerContext, PageContext, ProductCard, ProductInfo, ProductInfoResult, ProductSearchResult, SizeStock, Stock, StockLookupResult


@dataclass
class ShopDependencies:
    database: Path
    customer: CustomerContext | None = None
    page_context: PageContext = field(default_factory=PageContext)
    current_product: ProductCard | None = None
    seen_products: dict[str, ProductCard] = field(default_factory=dict)
    tool_names: list[str] = field(default_factory=list)
    lookup_results: list[ProductInfoResult | StockLookupResult] = field(default_factory=list)
    last_search: ProductSearchResult | None = None
    alternatives: AlternativeProductsResult | None = None
    audit: Any | None = None
    audit_run_id: str | None = None


def normalize_size(size: str | None) -> str | None:
    if size is None:
        return None
    value = re.sub(r"[\s_-]+", "", size.strip().upper())
    aliases = {"EXTRASMALL": "XS", "XSMALL": "XS", "SMALL": "S", "MEDIUM": "M", "LARGE": "L",
               "EXTRALARGE": "XL", "XLARGE": "XL", "XXLARGE": "XXL", "2XL": "XXL", "XXXL": "3XL"}
    return aliases.get(value, value)


def catalogue_only(action, table, column, database, trigger):
    if action == sqlite3.SQLITE_READ and table not in {"catalogue", "inventory"}:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def read_products(database: Path, product_id: str | None = None) -> list[ProductCard]:
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.set_authorizer(catalogue_only)
        db.execute("BEGIN")
        query = "SELECT product_id, name, garment_type, description, colors, search_tags, image_file_path, price FROM catalogue"
        params = ()
        if product_id is not None:
            query += " WHERE product_id = ?"
            params = (product_id,)
        rows = db.execute(query + " ORDER BY name", params).fetchall()
        stock_query = "SELECT product_id, size, quantity FROM inventory"
        if product_id is not None:
            stock_query += " WHERE product_id = ?"
        stock: dict[str, list[Stock]] = {}
        size_order = {size: i for i, size in enumerate(("XS", "S", "M", "L", "XL", "XXL"))}
        for entry in db.execute(stock_query, params):
            stock.setdefault(entry["product_id"], []).append(Stock(size=entry["size"], quantity=entry["quantity"]))
        products = []
        for row in rows:
            values = dict(row)
            image_path = (database.parent / values.pop("image_file_path")).resolve()
            relative = image_path.relative_to((database.parent / "products").resolve())
            values["image_url"] = "/api/images/" + quote(relative.as_posix(), safe="/")
            values["colors"] = json.loads(values["colors"])
            values["search_tags"] = json.loads(values["search_tags"])
            values["inventory"] = sorted(stock.get(row["product_id"], []), key=lambda s: (size_order.get(s.size, 99), s.size))
            products.append(ProductCard(**values))
        return products


def matching_products(database: Path, query: str = "", max_price: float | None = None,
                      size: str | None = None, in_stock_only: bool = False, limit: int | None = 6) -> list[ProductCard]:
    """Local matching over the small catalogue; send at most six matches to AI."""
    aliases = {"hoodies": "hood", "hoodie": "hood", "hooded": "hood",
               "sweatshirts": "sweatshirt", "shirts": "shirt", "tees": "shirt",
               "tshirts": "shirt", "tshirt": "shirt", "crewnecks": "crewneck"}
    terms = [aliases.get(term, term) for term in re.findall(r"[a-z0-9]+", query.lower())]
    terms = [term for term in terms if term not in {"a", "an", "the", "and", "for", "in", "with", "me", "show"}][:12]
    size = normalize_size(size)
    matches = []
    for product in read_products(database):
        searchable = " ".join([product.name, product.garment_type, product.description, *product.colors, *product.search_tags]).lower()
        if not all(term in searchable for term in terms):
            continue
        if max_price is not None and product.price > max_price:
            continue
        relevant_stock = [s for s in product.inventory if size is None or s.size.upper() == size.upper()]
        if size is not None and not relevant_stock:
            continue
        if in_stock_only and not any(s.quantity > 0 for s in relevant_stock):
            continue
        matches.append(product)
    return sorted(matches, key=lambda p: (p.price, p.name))[:limit]


def search_products(ctx: RunContext[ShopDependencies], query: str = "",
                    max_price: float | None = None, size: str | None = None,
                    in_stock_only: bool = False) -> ProductSearchResult:
    """Search the catalogue; return filters, exact match count and up to six cards, cheapest first.

    Args:
        query: Short product/color/theme keywords, e.g. 'navy hoodie'. Leave empty to browse.
        max_price: Optional inclusive maximum price in USD; use this rather than price words in query.
        size: Optional exact size label (XS, S, M, L, XL, XXL).
        in_stock_only: When true, require positive quantity in the requested size (or any size if none).
    """
    ctx.deps.tool_names.append("search_products")
    matches = matching_products(ctx.deps.database, query, max_price, size, in_stock_only, limit=None)
    result = ProductSearchResult(query=query.strip(), max_price=max_price, size=normalize_size(size),
                                 in_stock_only=in_stock_only, total_matches=len(matches), products=matches[:6])
    ctx.deps.seen_products.update({product.product_id: product for product in result.products})
    ctx.deps.last_search = result
    return result


def _lookup_product(deps: ShopDependencies, product_id: str) -> ProductCard | None:
    # Always reread SQLite. seen_products exists only to hydrate verified cards,
    # never as a cache for answering follow-up questions.
    products = read_products(deps.database, product_id)
    if not products:
        return None
    product = products[0]
    deps.seen_products[product.product_id] = product
    return product


def get_product_info(ctx: RunContext[ShopDependencies], product_id: str) -> ProductInfoResult:
    """Read one exact product's description, price in USD, type and colors from SQLite.

    Use search_products to identify an ID if needed, then call this for price or
    description questions. A missing ID returns found=false and product=null,
    never an invented price. Call again for follow-ups; do not reuse old prices.
    """
    ctx.deps.tool_names.append("get_product_info")
    product = _lookup_product(ctx.deps, product_id)
    result = _info_result(product_id, product)
    ctx.deps.lookup_results.append(result)
    return result


def get_stock(ctx: RunContext[ShopDependencies], product_id: str, size: str | None = None) -> StockLookupResult:
    """Read stock for one exact product, optionally for a requested size.

    Args:
        product_id: Exact catalogue ID; identify it with search_products if needed.
        size: Requested size (e.g. M or medium). Omit only for an all-size overview.

    Returns out_of_stock and quantity=0 for a recorded sold-out size.
    size_not_found, no_inventory and product_not_found have quantity=null:
    missing information does NOT mean sold out. Never substitute a different size.
    When size is omitted, quantity is the sum of all returned size rows, not a
    count available in every size. Read again for every follow-up stock question.
    """
    requested_size = normalize_size(size)
    if requested_size == "":
        raise ModelRetry("Provide a nonempty size label, or omit size for all recorded sizes.")
    ctx.deps.tool_names.append("get_stock")
    product = _lookup_product(ctx.deps, product_id)
    result = _stock_result(product_id, product, requested_size)
    ctx.deps.lookup_results.append(result)
    return result


def _info_result(product_id: str, product: ProductCard | None) -> ProductInfoResult:
    info = ProductInfo(**product.model_dump(include=set(ProductInfo.model_fields) - {"currency"})) if product else None
    return ProductInfoResult(product_id=product_id, found=product is not None, product=info)


def _stock_result(product_id: str, product: ProductCard | None, requested_size: str | None) -> StockLookupResult:
    base = dict(product_id=product_id, product_name=product.name if product else None, requested_size=requested_size)
    if product is None:
        result = StockLookupResult(**base, status="product_not_found")
    elif not product.inventory:
        result = StockLookupResult(**base, status="no_inventory")
    else:
        rows = [row for row in product.inventory if requested_size is None or row.size == requested_size]
        if not rows:
            result = StockLookupResult(**base, status="size_not_found")
        else:
            sizes = [SizeStock(size=row.size, quantity=row.quantity,
                               status="in_stock" if row.quantity > 0 else "out_of_stock") for row in rows]
            quantity = sum(row.quantity for row in rows)
            result = StockLookupResult(**base, status="in_stock" if quantity > 0 else "out_of_stock",
                                       quantity=quantity, sizes=sizes)
    return result


def get_product_details(ctx: RunContext[ShopDependencies], product_id: str,
                        size: str | None = None) -> ProductDetailsResult:
    """Read price, description, colors and size stock together in one fresh database snapshot.

    Prefer this for combined price-and-stock questions. Pass the requested size,
    or omit for all sizes. Unknown quantities remain null, never zero.
    """
    requested_size = normalize_size(size)
    if requested_size == "":
        raise ModelRetry("Provide a nonempty size, or omit size for all recorded sizes.")
    ctx.deps.tool_names.append("get_product_details")
    product = _lookup_product(ctx.deps, product_id)
    result = ProductDetailsResult(info=_info_result(product_id, product),
                                  stock=_stock_result(product_id, product, requested_size))
    ctx.deps.lookup_results.extend([result.info, result.stock])
    return result


def garment_family(garment_type: str) -> str:
    """Explicit category grouping; no semantic guesses about fit or fabric."""
    value = garment_type.lower()
    if "hood" in value:
        return "hoodies"
    if "t-shirt" in value or "t shirt" in value:
        return "T-shirts"
    if "long-sleeve" in value and "shirt" in value:
        return "long-sleeve shirts"
    if "crewneck" in value or "crew-neck" in value:
        return "crewneck sweatshirts"
    if "quarter-zip" in value:
        return "quarter-zip pullovers"
    if "jacket" in value:
        return "jackets"
    return value


def find_alternatives(ctx: RunContext[ShopDependencies], product_id: str, size: str,
                      max_price: float | None = None) -> AlternativeProductsResult:
    """Find up to four similar items with positive stock in the requested size.

    Exclude product_id, match its garment family, and honor the inclusive USD
    max_price if supplied. Ask the shopper for size if unknown; never invent one.
    Results are ordered by closeness to the source price, then price/name/ID.
    Empty results mean no match, not permission to relax a size or budget.
    """
    requested_size = normalize_size(size)
    if not requested_size:
        raise ModelRetry("Ask the shopper for a size, then pass a nonempty size label.")
    if max_price is not None and (not math.isfinite(max_price) or max_price < 0):
        raise ModelRetry("Use a nonnegative finite maximum price, or omit the budget.")
    ctx.deps.tool_names.append("find_alternatives")
    catalogue = read_products(ctx.deps.database)
    source = next((item for item in catalogue if item.product_id == product_id), None)
    category = garment_family(source.garment_type) if source else None
    matches = []
    if source:
        matches = [item for item in catalogue if item.product_id != product_id
                   and garment_family(item.garment_type) == category
                   and (max_price is None or item.price <= max_price)
                   and any(row.size == requested_size and row.quantity > 0 for row in item.inventory)]
        matches.sort(key=lambda item: (abs(item.price - source.price), item.price, item.name, item.product_id))
    result = AlternativeProductsResult(source_product_id=product_id, source_found=source is not None,
        matching_category=category, query=f"Alternatives to {source.name}" if source else "Similar items",
        max_price=max_price, size=requested_size, in_stock_only=True,
        total_matches=len(matches), products=matches[:4])
    ctx.deps.seen_products.update({item.product_id: item for item in result.products})
    ctx.deps.alternatives = result
    # Keep the public shelf contract unchanged; the source metadata is for the agent.
    ctx.deps.last_search = ProductSearchResult(**result.model_dump(include=set(ProductSearchResult.model_fields)))
    return result
