from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import Quote, QuoteStatus
from app.models.schemas import QuoteCreate, QuoteUpdate, QuoteResponse
from app.services.sevdesk_client import SevDeskClient
from datetime import datetime

router = APIRouter(prefix="/quotes", tags=["quotes"])


def generate_quote_number() -> str:
    """Generate a unique quote number."""
    return f"Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


@router.post("/", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    quote: QuoteCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new quote and optionally sync with SevDesk.
    """
    # Create quote in local database
    db_quote = Quote(
        quote_number=generate_quote_number(),
        customer_name=quote.customer_name,
        customer_email=quote.customer_email,
        description=quote.description,
        amount=quote.amount,
        tax_rate=quote.tax_rate,
        valid_until=quote.valid_until,
        status=QuoteStatus.DRAFT,
    )

    db.add(db_quote)
    await db.commit()
    await db.refresh(db_quote)

    return db_quote


@router.get("/", response_model=List[QuoteResponse])
async def list_quotes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    List all quotes with pagination.
    """
    result = await db.execute(select(Quote).offset(skip).limit(limit))
    quotes = result.scalars().all()
    return quotes


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific quote by ID.
    """
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found",
        )

    return quote


@router.put("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: int,
    quote_update: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing quote.
    """
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found",
        )

    # Update fields that were provided
    update_data = quote_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quote, field, value)

    await db.commit()
    await db.refresh(quote)

    return quote


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a quote.
    """
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found",
        )

    await db.delete(quote)
    await db.commit()


@router.post("/{quote_id}/sync-to-sevdesk", response_model=QuoteResponse)
async def sync_quote_to_sevdesk(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync a quote to SevDesk API.
    """
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote with id {quote_id} not found",
        )

    try:
        # Prepare data for SevDesk
        sevdesk_data = {
            "orderNumber": quote.quote_number,
            "contact": {"name": quote.customer_name},
            "orderDate": quote.created_at.isoformat() if quote.created_at else None,
            "status": "100",  # Draft status in SevDesk
            "taxRate": quote.tax_rate,
            "taxText": "Default tax",
            "currency": "EUR",
        }

        # Send to SevDesk
        client = SevDeskClient()
        if quote.sevdesk_id:
            response = await client.update_quote(quote.sevdesk_id, sevdesk_data)
        else:
            response = await client.create_quote(sevdesk_data)
            # Extract ID from response (adjust based on actual API response structure)
            if "objects" in response and len(response["objects"]) > 0:
                quote.sevdesk_id = str(response["objects"][0].get("id"))

        await db.commit()
        await db.refresh(quote)

        return quote

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync with SevDesk: {str(e)}",
        )
