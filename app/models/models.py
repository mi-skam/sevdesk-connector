from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class QuoteStatus(str, enum.Enum):
    """Status of a quote."""

    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONVERTED = "converted"


class InvoiceStatus(str, enum.Enum):
    """Status of an invoice."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Quote(Base):
    """Quote model for storing quote information."""

    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    sevdesk_id = Column(String, unique=True, nullable=True, index=True)
    quote_number = Column(String, unique=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    description = Column(Text)
    amount = Column(Float, nullable=False)
    tax_rate = Column(Float, default=19.0)
    status = Column(Enum(QuoteStatus), default=QuoteStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    valid_until = Column(DateTime(timezone=True))


class Invoice(Base):
    """Invoice model for storing invoice/billing information."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    sevdesk_id = Column(String, unique=True, nullable=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    quote_id = Column(Integer, nullable=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    description = Column(Text)
    amount = Column(Float, nullable=False)
    tax_rate = Column(Float, default=19.0)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    due_date = Column(DateTime(timezone=True))
