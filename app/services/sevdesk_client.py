import httpx
from typing import Dict, Any, Optional
from app.core.config import get_settings


class SevDeskClient:
    """Client for interacting with the SevDesk API."""

    def __init__(self):
        """Initialize the SevDesk API client."""
        settings = get_settings()
        self.base_url = settings.sevdesk_base_url
        self.api_key = settings.sevdesk_api_key
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the SevDesk API."""
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def create_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a quote in SevDesk.

        Args:
            quote_data: Quote data to send to SevDesk

        Returns:
            Response from SevDesk API
        """
        # This is a placeholder - actual SevDesk API endpoint structure
        # might be different. Adjust according to SevDesk API documentation.
        return await self._request("POST", "Order", data=quote_data)

    async def update_quote(self, quote_id: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a quote in SevDesk.

        Args:
            quote_id: SevDesk quote ID
            quote_data: Updated quote data

        Returns:
            Response from SevDesk API
        """
        return await self._request("PUT", f"Order/{quote_id}", data=quote_data)

    async def get_quote(self, quote_id: str) -> Dict[str, Any]:
        """
        Get a quote from SevDesk.

        Args:
            quote_id: SevDesk quote ID

        Returns:
            Quote data from SevDesk
        """
        return await self._request("GET", f"Order/{quote_id}")

    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an invoice in SevDesk.

        Args:
            invoice_data: Invoice data to send to SevDesk

        Returns:
            Response from SevDesk API
        """
        return await self._request("POST", "Invoice", data=invoice_data)

    async def update_invoice(
        self, invoice_id: str, invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an invoice in SevDesk.

        Args:
            invoice_id: SevDesk invoice ID
            invoice_data: Updated invoice data

        Returns:
            Response from SevDesk API
        """
        return await self._request("PUT", f"Invoice/{invoice_id}", data=invoice_data)

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get an invoice from SevDesk.

        Args:
            invoice_id: SevDesk invoice ID

        Returns:
            Invoice data from SevDesk
        """
        return await self._request("GET", f"Invoice/{invoice_id}")

    async def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Send an invoice via SevDesk.

        Args:
            invoice_id: SevDesk invoice ID

        Returns:
            Response from SevDesk API
        """
        return await self._request("POST", f"Invoice/{invoice_id}/sendViaEmail")
