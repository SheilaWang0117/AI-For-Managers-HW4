"""Shared catalogue and chat contracts for the API, agent, and frontend."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Stock(BaseModel):
    size: str
    quantity: int = Field(ge=0)


class ProductInfo(BaseModel):
    product_id: str
    name: str
    description: str
    garment_type: str
    colors: list[str]
    price: float = Field(ge=0, allow_inf_nan=False)
    currency: Literal["USD"] = "USD"


class ProductInfoResult(BaseModel):
    product_id: str
    found: bool
    product: ProductInfo | None = None

    @model_validator(mode="after")
    def consistent_product(self):
        if self.found != (self.product is not None):
            raise ValueError("A found product must include its recorded information")
        if self.product and self.product.product_id != self.product_id:
            raise ValueError("Product IDs must match")
        return self


class SizeStock(Stock):
    status: Literal["in_stock", "out_of_stock"]

    @model_validator(mode="after")
    def consistent_status(self):
        if self.status != ("in_stock" if self.quantity > 0 else "out_of_stock"):
            raise ValueError("Stock status must agree with the recorded quantity")
        return self


class StockLookupResult(BaseModel):
    product_id: str
    product_name: str | None = None
    requested_size: str | None = Field(default=None, description="Normalized requested size; null means all recorded sizes.")
    status: Literal["in_stock", "out_of_stock", "size_not_found", "product_not_found", "no_inventory"]
    quantity: int | None = Field(default=None, ge=0, description="Exact count for the requested size, or total across returned sizes when no size was requested. Null means unknown.")
    sizes: list[SizeStock] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_stock(self):
        known = self.status in {"in_stock", "out_of_stock"}
        if known:
            if not self.sizes or self.quantity != sum(row.quantity for row in self.sizes):
                raise ValueError("Known stock requires size rows and an exact matching total")
            if self.status != ("in_stock" if self.quantity > 0 else "out_of_stock"):
                raise ValueError("Stock status must agree with the quantity")
            if self.requested_size is not None and (len(self.sizes) != 1 or self.sizes[0].size != self.requested_size):
                raise ValueError("A requested-size result must contain only that size")
        elif self.quantity is not None or self.sizes:
            raise ValueError("Missing stock information must not imply a quantity")
        return self


class ProductCard(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_url: str
    price: float
    inventory: list[Stock]


class ProductSearchResult(BaseModel):
    query: str
    max_price: float | None = None
    size: str | None = None
    in_stock_only: bool = False
    total_matches: int = Field(ge=0)
    products: list[ProductCard] = Field(default_factory=list, max_length=6)


class ProductDetailsResult(BaseModel):
    info: ProductInfoResult
    stock: StockLookupResult

    @model_validator(mode="after")
    def same_product(self):
        if self.info.product_id != self.stock.product_id:
            raise ValueError("Information and stock must describe the same product")
        if self.info.found != (self.stock.status != "product_not_found"):
            raise ValueError("Information and stock must agree on product existence")
        return self


class AlternativeProductsResult(ProductSearchResult):
    products: list[ProductCard] = Field(default_factory=list, max_length=4)
    source_product_id: str
    source_found: bool
    matching_category: str | None = None


class CustomerContext(BaseModel):
    """Only these authenticated profile fields enter the model context."""
    name: str
    first_name: str | None = None
    email: str


class PageContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: Literal["home", "products", "product", "about", "account", "login", "create-account", "other"] = "other"
    product_id: str | None = Field(default=None, max_length=160, pattern=r"^[a-zA-Z0-9_-]+$")

    @model_validator(mode="after")
    def product_page(self):
        if (self.page == "product") != (self.product_id is not None):
            raise ValueError("Only a product page must include a product ID")
        return self


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1000)
    page_context: PageContext = Field(default_factory=PageContext)

    @field_validator("message", mode="before")
    @classmethod
    def trim_message(cls, value):
        return value.strip() if isinstance(value, str) else value


class AgentReply(BaseModel):
    """The model chooses verified IDs, never invents product card fields."""

    reply: str = Field(min_length=1, max_length=2500, description="Concise, friendly plain-text answer grounded in tool results.")
    product_ids: list[str] = Field(default_factory=list, max_length=4,
                                  description="Up to four IDs retrieved with catalogue tools during this turn; empty if none are relevant.")


class ChatReply(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    search: ProductSearchResult | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    search: ProductSearchResult | None = None
    page_context: PageContext | None = None


class ChatHistory(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
