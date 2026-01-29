# Backend Programming Patterns

This document distills the key backend programming patterns demonstrated in this codebase, using concrete examples from the SevDesk Connector project.

---

## Table of Contents

1. [Layered Architecture](#1-layered-architecture)
2. [Configuration Management](#2-configuration-management)
3. [Database & ORM Patterns](#3-database--orm-patterns)
4. [Data Validation with Pydantic](#4-data-validation-with-pydantic)
5. [Dependency Injection](#5-dependency-injection)
6. [Service Layer Pattern](#6-service-layer-pattern)
7. [RESTful API Design](#7-restful-api-design)
8. [Error Handling Patterns](#8-error-handling-patterns)

---

## 1. Layered Architecture

**What it is:** Separating code into distinct layers with clear responsibilities.

**Why it matters:** Makes code maintainable, testable, and easier to understand.

```
app/
├── main.py              # Entry point - wires everything together
├── core/                # Infrastructure layer
│   ├── config.py        # Configuration management
│   └── database.py      # Database setup
├── models/              # Data layer
│   ├── models.py        # ORM models (database structure)
│   └── schemas.py       # API schemas (request/response validation)
├── api/                 # Presentation layer (HTTP endpoints)
│   ├── quotes.py
│   └── invoices.py
└── services/            # Business logic layer
    └── sevdesk_client.py
```

**The key principle:** Each layer only knows about the layer directly below it:
- **API layer** → uses **Services** and **Models**
- **Services** → use **Database** and **Config**
- **Models** → define data structures

**Example from `main.py:38-40`:**
```python
# The main.py wires layers together without containing business logic
app.include_router(quotes.router)
app.include_router(invoices.router)
```

---

## 2. Configuration Management

**Pattern: Environment-based settings with Pydantic**

**File:** `app/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Required - must be set
    sevdesk_api_key: str

    # Optional with defaults
    sevdesk_base_url: str = "https://my.sevdesk.de/api/v1"
    database_url: str = "sqlite+aiosqlite:///./sevdesk.db"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",        # Load from .env file
        case_sensitive=False,   # SEVDESK_API_KEY = sevdesk_api_key
    )

@lru_cache()  # Singleton - only created once
def get_settings() -> Settings:
    return Settings()
```

**Key Takeaways:**

| Pattern | Why |
|---------|-----|
| Environment variables | Never hardcode secrets; different values per environment |
| Type hints | Automatic validation - wrong types fail fast |
| Defaults | Sensible defaults reduce configuration burden |
| `@lru_cache()` | Singleton pattern - settings parsed once, reused everywhere |
| `.env` file | Local development convenience without polluting shell |

**Usage pattern:**
```python
# Import anywhere
from app.core.config import get_settings
settings = get_settings()
print(settings.database_url)
```

---

## 3. Database & ORM Patterns

**Pattern: Async SQLAlchemy with Dependency Injection**

**File:** `app/core/database.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

settings = get_settings()

# 1. Create engine (connection pool)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL in debug mode
    future=True,          # Use SQLAlchemy 2.0 style
)

# 2. Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
)

# 3. Base class for all models
Base = declarative_base()

# 4. Initialize tables on startup
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 5. Dependency for getting sessions
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session  # Context manager ensures cleanup
```

**ORM Model Example from `app/models/models.py`:**

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
import enum

class QuoteStatus(str, enum.Enum):
    """Inheriting from str makes JSON serialization automatic"""
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONVERTED = "converted"

class Quote(Base):
    __tablename__ = "quotes"

    # Primary key with auto-increment
    id = Column(Integer, primary_key=True, index=True)

    # Unique external ID (nullable - set after sync)
    sevdesk_id = Column(String, unique=True, nullable=True, index=True)

    # Unique business identifier
    quote_number = Column(String, unique=True, index=True)

    # Required fields
    customer_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

    # Fields with defaults
    tax_rate = Column(Float, default=19.0)
    status = Column(Enum(QuoteStatus), default=QuoteStatus.DRAFT)

    # Automatic timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Key Patterns:**

| Pattern | Example | Why |
|---------|---------|-----|
| Index frequently queried columns | `index=True` | Performance |
| Use enums for constrained values | `Enum(QuoteStatus)` | Type safety |
| Server-side defaults | `server_default=func.now()` | Consistent timestamps |
| Auto-update timestamps | `onupdate=func.now()` | Audit trail |
| Foreign keys | `ForeignKey("quotes.id")` | Referential integrity |

---

## 4. Data Validation with Pydantic

**Pattern: Separate schemas for Create, Update, and Response**

**File:** `app/models/schemas.py`

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Base schema - shared fields
class QuoteBase(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None  # Email format validation
    description: Optional[str] = None
    amount: float = Field(..., gt=0)  # Must be greater than 0
    tax_rate: float = Field(default=19.0, ge=0, le=100)  # 0-100 range
    valid_until: Optional[datetime] = None

# Create schema - inherits base, used for POST
class QuoteCreate(QuoteBase):
    pass

# Update schema - ALL fields optional for partial updates
class QuoteUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    amount: Optional[float] = Field(None, gt=0)
    status: Optional[QuoteStatus] = None  # Can update status
    # ... other fields

# Response schema - adds read-only fields
class QuoteResponse(QuoteBase):
    id: int
    quote_number: str
    sevdesk_id: Optional[str] = None
    status: QuoteStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Allow ORM model → Pydantic conversion
```

**Schema Hierarchy Diagram:**
```
                    QuoteBase (shared input fields)
                   /                               \
          QuoteCreate                         QuoteResponse
          (POST body)                         (adds read-only fields)

          QuoteUpdate
          (all fields optional)
```

**Validation Constraints:**

| Constraint | Syntax | Meaning |
|------------|--------|---------|
| Required | `Field(...)` | Must be provided |
| Optional | `Optional[T] = None` | Can be omitted |
| Min/Max length | `min_length=1, max_length=200` | String length bounds |
| Numeric range | `gt=0`, `ge=0`, `le=100` | Greater than, greater-equal, less-equal |
| Email format | `EmailStr` | Valid email structure |

---

## 5. Dependency Injection

**Pattern: FastAPI's `Depends()` for automatic injection**

**Why:** Decouples components, enables testing, manages resource lifecycle.

**Database Session Injection from `app/api/quotes.py:34-58`:**
```python
from fastapi import Depends
from app.core.database import get_db

@router.post("/", response_model=QuoteResponse)
async def create_quote(
    quote: QuoteCreate,                      # Request body - auto-validated
    db: AsyncSession = Depends(get_db),      # Injected database session
):
    db_quote = Quote(
        quote_number=generate_quote_number(),
        customer_name=quote.customer_name,
        # ...
    )
    db.add(db_quote)
    await db.commit()
    await db.refresh(db_quote)
    return db_quote
```

**Service Injection from `app/api/quotes.py:22-31,145-149`:**
```python
# Lazy singleton pattern
_sevdesk_client: SevDeskClient = None

def get_sevdesk_client() -> SevDeskClient:
    global _sevdesk_client
    if _sevdesk_client is None:
        _sevdesk_client = SevDeskClient()
    return _sevdesk_client

# Usage in endpoint
@router.post("/{quote_id}/sync-to-sevdesk")
async def sync_quote_to_sevdesk(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    client: SevDeskClient = Depends(get_sevdesk_client),  # Injected!
):
    # Both db and client are injected
    ...
```

**Dependency Types:**

| Type | Example | Lifecycle |
|------|---------|-----------|
| Request-scoped | `get_db()` | New instance per request |
| Singleton | `get_sevdesk_client()` | Shared across requests |
| Cached | `get_settings()` with `@lru_cache` | Computed once, reused |

---

## 6. Service Layer Pattern

**Pattern: Encapsulate external API calls in a dedicated client class**

**File:** `app/services/sevdesk_client.py`

```python
import httpx
from typing import Dict, Any, Optional

class SevDeskClient:
    """Client for interacting with the SevDesk API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.sevdesk_base_url
        self.api_key = settings.sevdesk_api_key
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generic request method - DRY principle"""
        url = f"{self.base_url}/{endpoint}"
        client = await self._get_client()

        response = await client.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data,
            params=params,
        )
        response.raise_for_status()
        return response.json()

    # Public API methods - clear, focused interfaces
    async def create_quote(self, quote_data: Dict) -> Dict:
        return await self._request("POST", "Order", data=quote_data)

    async def update_quote(self, quote_id: str, quote_data: Dict) -> Dict:
        return await self._request("PUT", f"Order/{quote_id}", data=quote_data)

    async def get_quote(self, quote_id: str) -> Dict:
        return await self._request("GET", f"Order/{quote_id}")
```

**Key Patterns:**

| Pattern | Implementation | Benefit |
|---------|----------------|---------|
| Encapsulation | All API logic in one class | Easy to test/mock |
| DRY | `_request()` handles all HTTP | No code duplication |
| Lazy init | `_get_client()` | Resource efficiency |
| Configuration | Reads from settings | Easy to reconfigure |
| Timeout | `timeout=30.0` | Prevents hanging |

---

## 7. RESTful API Design

**Pattern: Resource-oriented URLs with standard HTTP methods**

**File:** `app/api/quotes.py`

```python
router = APIRouter(prefix="/quotes", tags=["quotes"])

# CREATE - POST /quotes/
@router.post("/", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(quote: QuoteCreate, db: AsyncSession = Depends(get_db)):
    ...

# LIST - GET /quotes/?skip=0&limit=100
@router.get("/", response_model=List[QuoteResponse])
async def list_quotes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).offset(skip).limit(limit))
    return result.scalars().all()

# READ - GET /quotes/{quote_id}
@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: int, db: AsyncSession = Depends(get_db)):
    ...

# UPDATE - PUT /quotes/{quote_id}
@router.put("/{quote_id}", response_model=QuoteResponse)
async def update_quote(quote_id: int, quote_update: QuoteUpdate, db: AsyncSession = Depends(get_db)):
    update_data = quote_update.model_dump(exclude_unset=True)  # Partial update
    for field, value in update_data.items():
        setattr(quote, field, value)
    ...

# DELETE - DELETE /quotes/{quote_id}
@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(quote_id: int, db: AsyncSession = Depends(get_db)):
    ...

# CUSTOM ACTION - POST /quotes/{quote_id}/sync-to-sevdesk
@router.post("/{quote_id}/sync-to-sevdesk", response_model=QuoteResponse)
async def sync_quote_to_sevdesk(quote_id: int, ...):
    ...
```

**REST Conventions:**

| Operation | Method | URL | Status Code |
|-----------|--------|-----|-------------|
| Create | POST | `/quotes/` | 201 Created |
| List | GET | `/quotes/` | 200 OK |
| Read | GET | `/quotes/{id}` | 200 OK |
| Update | PUT | `/quotes/{id}` | 200 OK |
| Delete | DELETE | `/quotes/{id}` | 204 No Content |
| Custom Action | POST | `/quotes/{id}/sync` | 200 OK |

**Pagination Pattern:**
```python
@router.get("/")
async def list_quotes(
    skip: int = 0,      # Offset
    limit: int = 100,   # Page size
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Quote).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

**Partial Update Pattern from `app/api/quotes.py:113-116`:**
```python
# Only update fields that were explicitly provided
update_data = quote_update.model_dump(exclude_unset=True)
for field, value in update_data.items():
    setattr(quote, field, value)
```

---

## 8. Error Handling Patterns

**Pattern: Consistent HTTP exceptions with meaningful messages**

**From `app/api/quotes.py`:**

```python
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# 404 - Resource not found
@router.get("/{quote_id}")
async def get_quote(quote_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found",
        )
    return quote

# 500 - External service failure with logging
@router.post("/{quote_id}/sync-to-sevdesk")
async def sync_quote_to_sevdesk(quote_id: int, ...):
    try:
        response = await client.create_quote(sevdesk_data)
    except Exception as e:
        logger.exception("Failed to sync quote to SevDesk")  # Logs full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync with SevDesk. Please check your API key and try again.",
        )
```

**HTTP Status Code Guide:**

| Code | When to Use | Example |
|------|-------------|---------|
| 200 | Success with body | GET, PUT |
| 201 | Created | POST that creates |
| 204 | Success, no body | DELETE |
| 400 | Bad request | Invalid input |
| 404 | Not found | Resource doesn't exist |
| 500 | Server error | External API failure |

**Error Response Structure:**
```json
{
    "detail": "Quote with id 123 not found"
}
```

**Logging Best Practices:**
```python
# Setup at module level
logger = logging.getLogger(__name__)

# Log with context
logger.info(f"Creating quote for {customer_name}")
logger.warning(f"Quote {quote_id} has expired")
logger.exception("Failed to sync")  # Includes full traceback
```

---

## Quick Reference: Common Patterns

### Database Query Patterns
```python
# Get one or None
result = await db.execute(select(Quote).where(Quote.id == id))
quote = result.scalar_one_or_none()

# Get list
result = await db.execute(select(Quote).offset(skip).limit(limit))
quotes = result.scalars().all()

# Create
db.add(new_quote)
await db.commit()
await db.refresh(new_quote)

# Update
setattr(quote, "status", new_status)
await db.commit()

# Delete
await db.delete(quote)
await db.commit()
```

### Application Lifecycle
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)
```

### ID Generation
```python
from datetime import datetime
import uuid

def generate_quote_number() -> str:
    return f"Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
# Example: Q-20250129-153045-a1b2c3
```

---

## Summary

| Pattern | File | Key Concept |
|---------|------|-------------|
| Layered Architecture | `app/` structure | Separate concerns into layers |
| Configuration | `core/config.py` | Environment variables + Pydantic |
| Database | `core/database.py` | Async SQLAlchemy + dependency injection |
| Models | `models/models.py` | ORM with enums, indexes, auto-timestamps |
| Schemas | `models/schemas.py` | Separate Create/Update/Response schemas |
| Dependency Injection | `Depends(get_db)` | Decouple and enable testing |
| Service Layer | `services/sevdesk_client.py` | Encapsulate external APIs |
| REST API | `api/quotes.py` | Resources + HTTP methods + status codes |
| Error Handling | `HTTPException` | Consistent errors with logging |

These patterns work together to create a maintainable, testable, and scalable backend application.
