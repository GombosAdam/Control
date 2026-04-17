"""
Mock NAV Online Számla 3.0 client for local testing.
Returns realistic test data without connecting to NAV.
"""

import uuid
import random
from datetime import datetime, timedelta


# Sample Hungarian company data for realistic responses
MOCK_COMPANIES = [
    {"tax": "12345678", "name": "Példa Szoftver Kft.", "city": "Budapest"},
    {"tax": "87654321", "name": "Teszt Kereskedelmi Zrt.", "city": "Debrecen"},
    {"tax": "11223344", "name": "Minta Szolgáltató Bt.", "city": "Szeged"},
    {"tax": "55667788", "name": "Demo Építőipari Kft.", "city": "Pécs"},
    {"tax": "99887766", "name": "Próba Logisztika Kft.", "city": "Győr"},
]

MOCK_ITEMS = [
    "Szoftverfejlesztési szolgáltatás",
    "IT tanácsadás",
    "Rendszergazda szolgáltatás",
    "Cloud hosting díj",
    "Irodaszer beszerzés",
    "Nyomtató kellékek",
    "Hálózati eszközök",
    "Laptop Lenovo ThinkPad",
    "Monitor Samsung 27\"",
    "Éves szoftver licensz",
]


class MockNAVOnlineSzamlaClient:
    """Mock client that simulates NAV API responses."""

    def __init__(self, login: str, password: str, signature_key: str,
                 replacement_key: str, tax_number: str,
                 environment: str = "test"):
        self.login = login
        self.tax_number = tax_number
        self._exchange_token = None

    async def token_exchange(self) -> str:
        self._exchange_token = f"MOCK-TOKEN-{uuid.uuid4().hex[:16].upper()}"
        return self._exchange_token

    async def query_invoice_digest(self, date_from: str, date_to: str,
                                    page: int = 1,
                                    direction: str = "INBOUND") -> dict:
        """Return mock invoice digests."""
        num_invoices = random.randint(3, 8)
        digests = []

        for i in range(num_invoices):
            supplier = random.choice(MOCK_COMPANIES)
            net = round(random.uniform(50000, 2000000), 0)
            vat = round(net * 0.27, 0)

            days_offset = random.randint(0, 30)
            issue_date = datetime.strptime(date_from, "%Y-%m-%d") + timedelta(days=days_offset)

            digests.append({
                "invoiceNumber": f"MOCK-{issue_date.strftime('%Y%m')}-{1000 + i}",
                "invoiceOperation": "CREATE",
                "invoiceCategory": "NORMAL",
                "invoiceIssueDate": issue_date.strftime("%Y-%m-%d"),
                "supplierTaxNumber": supplier["tax"],
                "supplierName": supplier["name"],
                "customerTaxNumber": self.tax_number,
                "customerName": "Saját Cég Kft.",
                "invoiceNetAmount": str(net),
                "invoiceNetAmountHUF": str(net),
                "invoiceVatAmount": str(vat),
                "invoiceVatAmountHUF": str(vat),
                "currency": "HUF",
            })

        return {
            "currentPage": page,
            "availablePage": 1,
            "invoiceDigests": digests,
        }

    async def query_invoice_data(self, invoice_number: str,
                                  direction: str = "INBOUND",
                                  supplier_tax_number: str | None = None) -> dict:
        """Return mock full invoice data."""
        supplier = None
        if supplier_tax_number:
            supplier = next((c for c in MOCK_COMPANIES if c["tax"] == supplier_tax_number), None)
        if not supplier:
            supplier = random.choice(MOCK_COMPANIES)

        num_lines = random.randint(1, 5)
        lines = []
        total_net = 0

        for j in range(num_lines):
            qty = round(random.uniform(1, 20), 1)
            unit_price = round(random.uniform(5000, 200000), 0)
            line_net = round(qty * unit_price, 0)
            line_vat_rate = 0.27
            line_vat = round(line_net * line_vat_rate, 0)
            line_gross = line_net + line_vat
            total_net += line_net

            lines.append({
                "lineNumber": str(j + 1),
                "lineDescription": random.choice(MOCK_ITEMS),
                "quantity": str(qty),
                "unitPrice": str(unit_price),
                "lineNetAmount": str(line_net),
                "lineVatRate": str(line_vat_rate),
                "lineVatAmount": str(line_vat),
                "lineGrossAmount": str(line_gross),
            })

        total_vat = round(total_net * 0.27, 0)
        total_gross = total_net + total_vat
        issue_date = datetime.utcnow().strftime("%Y-%m-%d")
        delivery_date = (datetime.utcnow() - timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d")
        payment_date = (datetime.utcnow() + timedelta(days=random.randint(8, 30))).strftime("%Y-%m-%d")

        return {
            "invoiceDataXml": "<mock>true</mock>",
            "compressedContentIndicator": "false",
            "parsedInvoice": {
                "supplier": {
                    "taxNumber": supplier["tax"],
                    "name": supplier["name"],
                    "address": supplier["city"],
                },
                "customer": {
                    "taxNumber": self.tax_number,
                    "name": "Saját Cég Kft.",
                },
                "header": {
                    "invoiceNumber": invoice_number,
                    "invoiceIssueDate": issue_date,
                    "invoiceDeliveryDate": delivery_date,
                    "paymentDate": payment_date,
                    "paymentMethod": "TRANSFER",
                    "currency": "HUF",
                    "invoiceAppearance": "ELECTRONIC",
                },
                "lines": lines,
                "summary": {
                    "invoiceNetAmount": str(total_net),
                    "invoiceVatAmount": str(total_vat),
                    "invoiceGrossAmount": str(total_gross),
                },
            },
        }

    async def query_taxpayer(self, query_tax_number: str) -> dict:
        """Return mock taxpayer validation."""
        known = next((c for c in MOCK_COMPANIES if c["tax"] == query_tax_number), None)
        if known:
            return {
                "taxpayerValidity": True,
                "taxpayerName": known["name"],
                "taxpayerShortName": known["name"].split()[0],
                "taxpayerAddressCity": known["city"],
            }
        # Unknown but valid-looking tax number
        if len(query_tax_number) >= 8 and query_tax_number.isdigit():
            return {
                "taxpayerValidity": True,
                "taxpayerName": f"Ismeretlen Cég ({query_tax_number})",
                "taxpayerShortName": "Ismeretlen",
                "taxpayerAddressCity": "Budapest",
            }
        return {
            "taxpayerValidity": False,
            "taxpayerName": None,
            "taxpayerShortName": None,
            "taxpayerAddressCity": None,
        }

    async def manage_invoice(self, invoice_operations: list[dict]) -> str:
        """Return mock transaction ID."""
        if not self._exchange_token:
            await self.token_exchange()
        return f"MOCK-TXN-{uuid.uuid4().hex[:20].upper()}"

    async def query_transaction_status(self, transaction_id: str) -> dict:
        """Return mock transaction status — always DONE."""
        return {
            "processingResults": [
                {
                    "index": "1",
                    "invoiceStatus": "DONE",
                    "originalRequestVersion": "3.0",
                    "businessValidationMessages": [],
                    "technicalValidationMessages": [],
                }
            ],
        }
