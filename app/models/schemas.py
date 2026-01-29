from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from app.models.models import QuoteStatus, InvoiceStatus


# Quote Schemas
class QuoteBase(BaseModel):
    """Base schema for quote data."""

    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    tax_rate: float = Field(default=19.0, ge=0, le=100)
    valid_until: Optional[datetime] = None


class QuoteCreate(QuoteBase):
    """Schema for creating a new quote."""

    pass


class QuoteUpdate(BaseModel):
    """Schema for updating an existing quote."""

    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    tax_rate: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[QuoteStatus] = None
    valid_until: Optional[datetime] = None


class QuoteResponse(QuoteBase):
    """Schema for quote response."""

    id: int
    quote_number: str
    sevdesk_id: Optional[str] = None
    status: QuoteStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceBase(BaseModel):
    """Base schema for invoice data."""

    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    tax_rate: float = Field(default=19.0, ge=0, le=100)
    due_date: Optional[datetime] = None
    quote_id: Optional[int] = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating a new invoice."""

    pass


class InvoiceUpdate(BaseModel):
    """Schema for updating an existing invoice."""

    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    tax_rate: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[InvoiceStatus] = None
    due_date: Optional[datetime] = None


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response."""

    id: int
    invoice_number: str
    sevdesk_id: Optional[str] = None
    status: InvoiceStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
