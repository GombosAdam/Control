"""
Build XML requests for NAV Online Számla 3.0 API.
"""

import uuid
from datetime import datetime
from lxml import etree

API_NS = "http://schemas.nav.gov.hu/OSA/3.0/api"
DATA_NS = "http://schemas.nav.gov.hu/OSA/3.0/data"
COMMON_NS = "http://schemas.nav.gov.hu/NTCA/1.0/common"

NSMAP_API = {
    None: API_NS,
    "common": COMMON_NS,
}

NSMAP_DATA = {
    None: DATA_NS,
}


def _generate_request_id() -> str:
    """Generate a 30-char unique request ID (NAV max length)."""
    return "RID" + uuid.uuid4().hex[:27].upper()


def _format_timestamp(dt: datetime | None = None) -> str:
    """Format timestamp as yyyyMMddHHmmss for NAV."""
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y%m%d%H%M%S")


def _add_header(parent: etree._Element, request_id: str, timestamp: str,
                request_signature: str, login: str, encrypted_password: str,
                tax_number: str) -> None:
    """Add common header and user elements to a NAV API request."""
    header = etree.SubElement(parent, f"{{{COMMON_NS}}}header")
    etree.SubElement(header, f"{{{COMMON_NS}}}requestId").text = request_id
    etree.SubElement(header, f"{{{COMMON_NS}}}timestamp").text = timestamp
    etree.SubElement(header, f"{{{COMMON_NS}}}requestVersion").text = "3.0"
    etree.SubElement(header, f"{{{COMMON_NS}}}headerVersion").text = "1.0"

    user = etree.SubElement(parent, f"{{{COMMON_NS}}}user")
    etree.SubElement(user, f"{{{COMMON_NS}}}login").text = login
    pw_hash = etree.SubElement(user, f"{{{COMMON_NS}}}passwordHash")
    pw_hash.text = encrypted_password
    pw_hash.set("cryptoType", "AES-128-ECB")
    etree.SubElement(user, f"{{{COMMON_NS}}}taxNumber").text = tax_number
    etree.SubElement(user, f"{{{COMMON_NS}}}requestSignature").\
        text = request_signature
    pw_hash_2 = etree.SubElement(user, f"{{{COMMON_NS}}}requestSignature")
    # Fix: signature is on user, remove duplicate — restructure
    # Actually NAV schema puts requestSignature directly under user
    # Let's rebuild properly:

    # Remove incorrect elements and rebuild
    parent.remove(user)
    user = etree.SubElement(parent, f"{{{COMMON_NS}}}user")
    etree.SubElement(user, f"{{{COMMON_NS}}}login").text = login
    pw_hash = etree.SubElement(user, f"{{{COMMON_NS}}}passwordHash")
    pw_hash.text = encrypted_password
    pw_hash.set("cryptoType", "AES-128-ECB")
    etree.SubElement(user, f"{{{COMMON_NS}}}taxNumber").text = tax_number
    etree.SubElement(user, f"{{{COMMON_NS}}}requestSignature").text = request_signature


def build_token_exchange_request(request_id: str, timestamp: str,
                                  request_signature: str, login: str,
                                  encrypted_password: str, tax_number: str) -> str:
    """Build TokenExchangeRequest XML."""
    root = etree.Element(f"{{{API_NS}}}TokenExchangeRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)
    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_query_invoice_digest_request(request_id: str, timestamp: str,
                                        request_signature: str, login: str,
                                        encrypted_password: str, tax_number: str,
                                        date_from: str, date_to: str,
                                        page: int = 1,
                                        direction: str = "INBOUND") -> str:
    """Build QueryInvoiceDigestRequest XML for listing invoices."""
    root = etree.Element(f"{{{API_NS}}}QueryInvoiceDigestRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)

    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"

    etree.SubElement(root, f"{{{API_NS}}}page").text = str(page)
    etree.SubElement(root, f"{{{API_NS}}}invoiceDirection").text = direction

    mandatory_params = etree.SubElement(root, f"{{{API_NS}}}invoiceQueryParams")
    mandatory = etree.SubElement(mandatory_params, f"{{{API_NS}}}mandatoryQueryParams")
    date_range = etree.SubElement(mandatory, f"{{{API_NS}}}invoiceIssueDate")
    etree.SubElement(date_range, f"{{{API_NS}}}dateFrom").text = date_from
    etree.SubElement(date_range, f"{{{API_NS}}}dateTo").text = date_to

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_query_invoice_data_request(request_id: str, timestamp: str,
                                      request_signature: str, login: str,
                                      encrypted_password: str, tax_number: str,
                                      invoice_number: str, invoice_direction: str = "INBOUND",
                                      supplier_tax_number: str | None = None) -> str:
    """Build QueryInvoiceDataRequest XML to get full invoice data."""
    root = etree.Element(f"{{{API_NS}}}QueryInvoiceDataRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)

    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"

    inv_num_query = etree.SubElement(root, f"{{{API_NS}}}invoiceNumberQuery")
    etree.SubElement(inv_num_query, f"{{{API_NS}}}invoiceNumber").text = invoice_number
    etree.SubElement(inv_num_query, f"{{{API_NS}}}invoiceDirection").text = invoice_direction
    if supplier_tax_number:
        etree.SubElement(inv_num_query, f"{{{API_NS}}}supplierTaxNumber").text = supplier_tax_number

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_query_taxpayer_request(request_id: str, timestamp: str,
                                  request_signature: str, login: str,
                                  encrypted_password: str, tax_number: str,
                                  query_tax_number: str) -> str:
    """Build QueryTaxpayerRequest XML."""
    root = etree.Element(f"{{{API_NS}}}QueryTaxpayerRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)

    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"

    etree.SubElement(root, f"{{{API_NS}}}taxNumber").text = query_tax_number
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_manage_invoice_request(request_id: str, timestamp: str,
                                  request_signature: str, login: str,
                                  encrypted_password: str, tax_number: str,
                                  exchange_token: str,
                                  invoice_operations: list[dict]) -> str:
    """
    Build ManageInvoiceRequest XML for submitting invoices.
    invoice_operations: list of {operation: str, invoice_data_base64: str}
    Max 100 per request.
    """
    root = etree.Element(f"{{{API_NS}}}ManageInvoiceRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)

    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"

    etree.SubElement(root, f"{{{API_NS}}}exchangeToken").text = exchange_token

    ops = etree.SubElement(root, f"{{{API_NS}}}invoiceOperations")
    etree.SubElement(ops, f"{{{API_NS}}}compressedContent").text = "false"
    for idx, op in enumerate(invoice_operations, start=1):
        inv_op = etree.SubElement(ops, f"{{{API_NS}}}invoiceOperation")
        etree.SubElement(inv_op, f"{{{API_NS}}}index").text = str(idx)
        etree.SubElement(inv_op, f"{{{API_NS}}}invoiceOperation").text = op["operation"]
        etree.SubElement(inv_op, f"{{{API_NS}}}invoiceData").text = op["invoice_data_base64"]

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def build_query_transaction_status_request(request_id: str, timestamp: str,
                                            request_signature: str, login: str,
                                            encrypted_password: str, tax_number: str,
                                            transaction_id: str) -> str:
    """Build QueryTransactionStatusRequest XML."""
    root = etree.Element(f"{{{API_NS}}}QueryTransactionStatusRequest", nsmap=NSMAP_API)
    _add_header(root, request_id, timestamp, request_signature,
                login, encrypted_password, tax_number)

    software = etree.SubElement(root, f"{{{API_NS}}}software")
    etree.SubElement(software, f"{{{API_NS}}}softwareId").text = "INVMGR01000001"
    etree.SubElement(software, f"{{{API_NS}}}softwareName").text = "Invoice Manager"
    etree.SubElement(software, f"{{{API_NS}}}softwareOperation").text = "LOCAL_SOFTWARE"
    etree.SubElement(software, f"{{{API_NS}}}softwareMainVersion").text = "1.0"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevName").text = "Invoice Manager Dev"
    etree.SubElement(software, f"{{{API_NS}}}softwareDevContact").text = "dev@invoicemanager.hu"

    etree.SubElement(root, f"{{{API_NS}}}transactionId").text = transaction_id
    etree.SubElement(root, f"{{{API_NS}}}returnOriginalRequest").text = "false"

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")
