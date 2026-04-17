"""
Parse XML responses from NAV Online Számla 3.0 API.
"""

import base64
from lxml import etree

API_NS = "http://schemas.nav.gov.hu/OSA/3.0/api"
DATA_NS = "http://schemas.nav.gov.hu/OSA/3.0/data"
COMMON_NS = "http://schemas.nav.gov.hu/NTCA/1.0/common"

NS = {
    "api": API_NS,
    "data": DATA_NS,
    "common": COMMON_NS,
}


def _find_text(el: etree._Element, xpath: str, default: str | None = None) -> str | None:
    """Find text in an element using namespace-aware XPath."""
    node = el.find(xpath, namespaces=NS)
    if node is not None and node.text:
        return node.text.strip()
    return default


def parse_general_error(xml_bytes: bytes) -> dict | None:
    """Parse funcCode and error info from any NAV response."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None

    result = _find_text(root, ".//api:funcCode") or _find_text(root, ".//common:funcCode")
    if not result:
        return None

    error_code = _find_text(root, ".//api:errorCode") or _find_text(root, ".//common:errorCode")
    message = _find_text(root, ".//api:message") or _find_text(root, ".//common:message")

    return {
        "funcCode": result,
        "errorCode": error_code,
        "message": message,
    }


def parse_token_exchange_response(xml_bytes: bytes) -> dict:
    """Parse TokenExchangeResponse → {encodedExchangeToken, tokenValidityFrom, tokenValidityTo}."""
    root = etree.fromstring(xml_bytes)
    return {
        "encodedExchangeToken": _find_text(root, ".//api:encodedExchangeToken"),
        "tokenValidityFrom": _find_text(root, ".//api:tokenValidityFrom"),
        "tokenValidityTo": _find_text(root, ".//api:tokenValidityTo"),
    }


def parse_query_invoice_digest_response(xml_bytes: bytes) -> dict:
    """Parse QueryInvoiceDigestResponse → {currentPage, availablePage, invoiceDigests: [...]}."""
    root = etree.fromstring(xml_bytes)

    digests = []
    for digest_el in root.findall(".//api:invoiceDigest", namespaces=NS):
        digests.append({
            "invoiceNumber": _find_text(digest_el, "api:invoiceNumber"),
            "invoiceOperation": _find_text(digest_el, "api:invoiceOperation"),
            "invoiceCategory": _find_text(digest_el, "api:invoiceCategory"),
            "invoiceIssueDate": _find_text(digest_el, "api:invoiceIssueDate"),
            "supplierTaxNumber": _find_text(digest_el, "api:supplierTaxNumber"),
            "supplierName": _find_text(digest_el, "api:supplierName"),
            "customerTaxNumber": _find_text(digest_el, "api:customerTaxNumber"),
            "customerName": _find_text(digest_el, "api:customerName"),
            "invoiceNetAmount": _find_text(digest_el, "api:invoiceNetAmount"),
            "invoiceNetAmountHUF": _find_text(digest_el, "api:invoiceNetAmountHUF"),
            "invoiceVatAmount": _find_text(digest_el, "api:invoiceVatAmount"),
            "invoiceVatAmountHUF": _find_text(digest_el, "api:invoiceVatAmountHUF"),
            "currency": _find_text(digest_el, "api:currency"),
        })

    return {
        "currentPage": int(_find_text(root, ".//api:currentPage") or "1"),
        "availablePage": int(_find_text(root, ".//api:availablePage") or "1"),
        "invoiceDigests": digests,
    }


def parse_query_invoice_data_response(xml_bytes: bytes) -> dict:
    """Parse QueryInvoiceDataResponse → invoice data XML (base64 decoded)."""
    root = etree.fromstring(xml_bytes)

    invoice_data_b64 = _find_text(root, ".//api:invoiceData")
    decoded_xml = None
    if invoice_data_b64:
        decoded_xml = base64.b64decode(invoice_data_b64).decode("utf-8")

    return {
        "invoiceDataXml": decoded_xml,
        "compressedContentIndicator": _find_text(root, ".//api:compressedContentIndicator"),
    }


def parse_invoice_data_xml(invoice_xml: str) -> dict:
    """Parse the inner invoice data XML into a structured dict."""
    root = etree.fromstring(invoice_xml.encode("utf-8"))

    def _t(xpath: str) -> str | None:
        return _find_text(root, xpath)

    # Supplier info
    supplier = {
        "taxNumber": _t(".//data:supplierInfo/data:supplierTaxNumber/data:taxpayerId"),
        "name": _t(".//data:supplierInfo/data:supplierName"),
        "address": _t(".//data:supplierInfo/data:supplierAddress/data:simpleAddress/data:city"),
    }

    # Customer info
    customer = {
        "taxNumber": _t(".//data:customerInfo/data:customerTaxNumber/data:taxpayerId"),
        "name": _t(".//data:customerInfo/data:customerName"),
    }

    # Invoice header
    header = {
        "invoiceNumber": _t(".//data:invoiceNumber"),
        "invoiceIssueDate": _t(".//data:invoiceIssueDate"),
        "invoiceDeliveryDate": _t(".//data:invoiceDeliveryDate"),
        "paymentDate": _t(".//data:paymentDate"),
        "paymentMethod": _t(".//data:paymentMethod"),
        "currency": _t(".//data:currencyCode"),
        "invoiceAppearance": _t(".//data:invoiceAppearance"),
    }

    # Lines
    lines = []
    for line_el in root.findall(".//data:line", namespaces=NS):
        lines.append({
            "lineNumber": _find_text(line_el, "data:lineNumber"),
            "lineDescription": _find_text(line_el, "data:lineDescription"),
            "quantity": _find_text(line_el, "data:quantity"),
            "unitPrice": _find_text(line_el, "data:unitPrice"),
            "lineNetAmount": _find_text(line_el, "data:lineAmountsNormal/data:lineNetAmountData/data:lineNetAmount"),
            "lineVatRate": _find_text(line_el, "data:lineAmountsNormal/data:lineVatRate/data:vatPercentage"),
            "lineVatAmount": _find_text(line_el, "data:lineAmountsNormal/data:lineVatData/data:lineVatAmount"),
            "lineGrossAmount": _find_text(line_el, "data:lineAmountsNormal/data:lineGrossAmountData/data:lineGrossAmountNormal"),
        })

    # Summary
    summary = {
        "invoiceNetAmount": _t(".//data:invoiceSummary/data:summaryNormal/data:invoiceNetAmount"),
        "invoiceVatAmount": _t(".//data:invoiceSummary/data:summaryNormal/data:invoiceVatAmount"),
        "invoiceGrossAmount": _t(".//data:invoiceSummary/data:summaryGrossData/data:invoiceGrossAmount"),
    }

    return {
        "supplier": supplier,
        "customer": customer,
        "header": header,
        "lines": lines,
        "summary": summary,
    }


def parse_query_taxpayer_response(xml_bytes: bytes) -> dict:
    """Parse QueryTaxpayerResponse → taxpayer info."""
    root = etree.fromstring(xml_bytes)

    taxpayer_validity = _find_text(root, ".//api:taxpayerValidity")
    name = _find_text(root, ".//api:taxpayerName")
    short_name = _find_text(root, ".//api:taxpayerShortName")
    address = _find_text(root, ".//api:taxpayerAddress//api:city")

    return {
        "taxpayerValidity": taxpayer_validity == "true" if taxpayer_validity else None,
        "taxpayerName": name,
        "taxpayerShortName": short_name,
        "taxpayerAddressCity": address,
    }


def parse_manage_invoice_response(xml_bytes: bytes) -> dict:
    """Parse ManageInvoiceResponse → transactionId."""
    root = etree.fromstring(xml_bytes)
    return {
        "transactionId": _find_text(root, ".//api:transactionId"),
    }


def parse_query_transaction_status_response(xml_bytes: bytes) -> dict:
    """Parse QueryTransactionStatusResponse → processing results."""
    root = etree.fromstring(xml_bytes)

    results = []
    for pr in root.findall(".//api:processingResult", namespaces=NS):
        result = {
            "index": _find_text(pr, "api:index"),
            "invoiceStatus": _find_text(pr, "api:invoiceStatus"),
            "originalRequestVersion": _find_text(pr, "api:originalRequestVersion"),
        }
        # Business validation messages
        messages = []
        for msg in pr.findall(".//api:businessValidationMessage", namespaces=NS):
            messages.append({
                "validationResultCode": _find_text(msg, "api:validationResultCode"),
                "validationErrorCode": _find_text(msg, "api:validationErrorCode"),
                "message": _find_text(msg, "api:message"),
            })
        result["businessValidationMessages"] = messages

        # Technical validation messages
        tech_msgs = []
        for msg in pr.findall(".//api:technicalValidationMessage", namespaces=NS):
            tech_msgs.append({
                "validationResultCode": _find_text(msg, "api:validationResultCode"),
                "validationErrorCode": _find_text(msg, "api:validationErrorCode"),
                "message": _find_text(msg, "api:message"),
            })
        result["technicalValidationMessages"] = tech_msgs

        results.append(result)

    return {
        "processingResults": results,
    }
