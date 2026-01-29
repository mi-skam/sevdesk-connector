from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import Invoice, InvoiceStatus
from app.models.schemas import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from app.services.sevdesk_client import SevDeskClient
from datetime import datetime

router = APIRouter(prefix="/invoices", tags=["invoices"])


def generate_invoice_number() -> str:
    """Generate a unique invoice number."""
    return f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new invoice and optionally sync with SevDesk.
    """
    # Create invoice in local database
    db_invoice = Invoice(
        invoice_number=generate_invoice_number(),
        customer_name=invoice.customer_name,
        customer_email=invoice.customer_email,
        description=invoice.description,
        amount=invoice.amount,
        tax_rate=invoice.tax_rate,
        due_date=invoice.due_date,
        quote_id=invoice.quote_id,
        status=InvoiceStatus.DRAFT,
    )

    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)

    return db_invoice


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    List all invoices with pagination.
    """
    result = await db.execute(select(Invoice).offset(skip).limit(limit))
    invoices = result.scalars().all()
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific invoice by ID.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found",
        )

    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing invoice.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found",
        )

    # Update fields that were provided
    update_data = invoice_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    await db.commit()
    await db.refresh(invoice)

    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an invoice.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found",
        )

    await db.delete(invoice)
    await db.commit()


@router.post("/{invoice_id}/sync-to-sevdesk", response_model=InvoiceResponse)
async def sync_invoice_to_sevdesk(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync an invoice to SevDesk API.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found",
        )

    try:
        # Prepare data for SevDesk
        sevdesk_data = {
            "invoiceNumber": invoice.invoice_number,
            "contact": {"name": invoice.customer_name},
            "invoiceDate": invoice.created_at.isoformat() if invoice.created_at else None,
            "status": "100",  # Draft status in SevDesk
            "taxRate": invoice.tax_rate,
            "taxText": "Default tax",
            "currency": "EUR",
        }

        # Send to SevDesk
        client = SevDeskClient()
        if invoice.sevdesk_id:
            response = await client.update_invoice(invoice.sevdesk_id, sevdesk_data)
        else:
            response = await client.create_invoice(sevdesk_data)
            # Extract ID from response (adjust based on actual API response structure)
            if "objects" in response and len(response["objects"]) > 0:
                invoice.sevdesk_id = str(response["objects"][0].get("id"))

        await db.commit()
        await db.refresh(invoice)

        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync with SevDesk: {str(e)}",
        )


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Send an invoice via SevDesk email.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found",
        )

    if not invoice.sevdesk_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must be synced to SevDesk before sending",
        )

    try:
        client = SevDeskClient()
        await client.send_invoice(invoice.sevdesk_id)

        # Update status
        invoice.status = InvoiceStatus.SENT
        await db.commit()
        await db.refresh(invoice)

        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invoice: {str(e)}",
        )
