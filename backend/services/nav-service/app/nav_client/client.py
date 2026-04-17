"""
NAV Online Számla 3.0 API client.
"""

import logging
from datetime import datetime

import httpx

from app.nav_client.crypto import compute_request_signature, encrypt_password_aes128_ecb
from app.nav_client.xml_builder import (
    _generate_request_id, _format_timestamp,
    build_token_exchange_request,
    build_query_invoice_digest_request,
    build_query_invoice_data_request,
    build_query_taxpayer_request,
    build_manage_invoice_request,
    build_query_transaction_status_request,
)
from app.nav_client.xml_parser import (
    parse_general_error,
    parse_token_exchange_response,
    parse_query_invoice_digest_response,
    parse_query_invoice_data_response,
    parse_invoice_data_xml,
    parse_query_taxpayer_response,
    parse_manage_invoice_response,
    parse_query_transaction_status_response,
)
from app.nav_client.exceptions import NAVApiError, NAVAuthError, NAVConnectionError

logger = logging.getLogger(__name__)

NAV_TEST_URL = "https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3"
NAV_PROD_URL = "https://api.onlineszamla.nav.gov.hu/invoiceService/v3"


class NAVOnlineSzamlaClient:
    """Async client for NAV Online Számla 3.0 API."""

    def __init__(self, login: str, password: str, signature_key: str,
                 replacement_key: str, tax_number: str,
                 environment: str = "test"):
        self.login = login
        self.password = password
        self.signature_key = signature_key
        self.replacement_key = replacement_key
        self.tax_number = tax_number
        self.base_url = NAV_TEST_URL if environment == "test" else NAV_PROD_URL
        self._exchange_token: str | None = None

    def _prepare_auth(self) -> tuple[str, str, str, str]:
        """Prepare request_id, timestamp, signature, encrypted_password."""
        request_id = _generate_request_id()
        timestamp = _format_timestamp()
        signature = compute_request_signature(request_id, timestamp, self.signature_key)
        encrypted_pw = encrypt_password_aes128_ecb(self.password, self.replacement_key)
        return request_id, timestamp, signature, encrypted_pw

    async def _post(self, endpoint: str, xml_body: str) -> bytes:
        """Send POST request to NAV API and return response bytes."""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, content=xml_body.encode("utf-8"), headers=headers)
        except httpx.ConnectError as e:
            raise NAVConnectionError(f"Cannot connect to NAV API: {e}") from e
        except httpx.TimeoutException as e:
            raise NAVConnectionError(f"NAV API timeout: {e}") from e

        # Check for API-level errors
        if response.status_code != 200:
            error_info = parse_general_error(response.content)
            if error_info:
                raise NAVApiError(
                    error_info.get("funcCode", "ERROR"),
                    error_info.get("errorCode", "UNKNOWN"),
                    error_info.get("message", f"HTTP {response.status_code}"),
                )
            raise NAVApiError("ERROR", "HTTP_ERROR", f"HTTP {response.status_code}: {response.text[:500]}")

        # Check funcCode in successful responses too
        error_info = parse_general_error(response.content)
        if error_info and error_info["funcCode"] == "ERROR":
            raise NAVApiError(
                "ERROR",
                error_info.get("errorCode", "UNKNOWN"),
                error_info.get("message", "Unknown NAV error"),
            )

        return response.content

    async def token_exchange(self) -> str:
        """Get exchange token from NAV. Returns the token string."""
        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_token_exchange_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number,
        )
        response_bytes = await self._post("tokenExchange", xml)
        parsed = parse_token_exchange_response(response_bytes)
        token = parsed.get("encodedExchangeToken")
        if not token:
            raise NAVAuthError("No exchange token in response")
        self._exchange_token = token
        return token

    async def query_invoice_digest(self, date_from: str, date_to: str,
                                    page: int = 1,
                                    direction: str = "INBOUND") -> dict:
        """Query invoice digests (list) by date range."""
        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_query_invoice_digest_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number, date_from, date_to, page, direction,
        )
        response_bytes = await self._post("queryInvoiceDigest", xml)
        return parse_query_invoice_digest_response(response_bytes)

    async def query_invoice_data(self, invoice_number: str,
                                  direction: str = "INBOUND",
                                  supplier_tax_number: str | None = None) -> dict:
        """Get full invoice data for a specific invoice number."""
        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_query_invoice_data_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number, invoice_number, direction,
            supplier_tax_number,
        )
        response_bytes = await self._post("queryInvoiceData", xml)
        result = parse_query_invoice_data_response(response_bytes)
        if result.get("invoiceDataXml"):
            result["parsedInvoice"] = parse_invoice_data_xml(result["invoiceDataXml"])
        return result

    async def query_taxpayer(self, query_tax_number: str) -> dict:
        """Validate a tax number against NAV register."""
        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_query_taxpayer_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number, query_tax_number,
        )
        response_bytes = await self._post("queryTaxpayer", xml)
        return parse_query_taxpayer_response(response_bytes)

    async def manage_invoice(self, invoice_operations: list[dict]) -> str:
        """
        Submit invoices to NAV. Returns transactionId.
        invoice_operations: [{operation: 'CREATE', invoice_data_base64: '...'}]
        """
        if not self._exchange_token:
            await self.token_exchange()

        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_manage_invoice_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number, self._exchange_token,
            invoice_operations,
        )
        response_bytes = await self._post("manageInvoice", xml)
        parsed = parse_manage_invoice_response(response_bytes)
        txn_id = parsed.get("transactionId")
        if not txn_id:
            raise NAVApiError("ERROR", "NO_TXN_ID", "No transactionId in response")
        return txn_id

    async def query_transaction_status(self, transaction_id: str) -> dict:
        """Query status of a previously submitted transaction."""
        request_id, timestamp, signature, encrypted_pw = self._prepare_auth()
        xml = build_query_transaction_status_request(
            request_id, timestamp, signature, self.login,
            encrypted_pw, self.tax_number, transaction_id,
        )
        response_bytes = await self._post("queryTransactionStatus", xml)
        return parse_query_transaction_status_response(response_bytes)
