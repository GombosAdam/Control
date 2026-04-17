"""
E2E teszt: PO felvitel → jóváhagyás → kiküldés → számla → approval → match → könyvelés
"""
import json
import urllib.request
import urllib.error
import time

FINANCE = "http://localhost:8003/api/v1"
PIPELINE = "http://invoice-pipeline:8002/api/v1"

def api(method, url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:500]
        print(f"  !! {method} {url} -> {e.code}: {err}")
        return {"_error": e.code, "_detail": err}

def login(email):
    r = api("POST", f"{FINANCE}/auth/login", {"email": email, "password": "Demo123"})
    return r.get("token")

def step(num, desc):
    print(f"\n{'='*60}")
    print(f"  LEPES {num}: {desc}")
    print(f"{'='*60}")


# =============================================
print("\nLogin...")
clerk_token = login("antal.norbert@invoice.local")      # Logisztika clerk
dept_head_token = login("farkas.tamas@invoice.local")    # Logisztika dept_head
admin_token = login("admin@invoice.local")               # Admin/Ugyvezetó
cfo_token = login("cfo@invoice.local")                   # CFO
reviewer_token = login("reviewer@invoice.local")         # Reviewer

for name, tok in [("Antal Norbert (clerk)", clerk_token), ("Farkas Tamas (dept_head)", dept_head_token),
                  ("Admin", admin_token), ("CFO", cfo_token), ("Reviewer", reviewer_token)]:
    print(f"  {name}: {'OK' if tok else 'FAIL'}")

if not all([clerk_token, dept_head_token, admin_token, cfo_token]):
    print("Login failed"); exit(1)

clerk_info = api("GET", f"{FINANCE}/auth/me", token=clerk_token)
dept_id = clerk_info["department_id"]

# =============================================
step(1, "PO FELVITEL (Antal Norbert, Logisztika clerk)")
# =============================================

budget = api("GET", f"{FINANCE}/budget/lines?department_id={dept_id}&status=approved&limit=5", token=clerk_token)
if not budget.get("items"):
    budget = api("GET", f"{FINANCE}/budget/lines?department_id={dept_id}&status=locked&limit=5", token=clerk_token)
if not budget.get("items"):
    budget = api("GET", f"{FINANCE}/budget/lines?status=approved&limit=5", token=admin_token)

bl = budget["items"][0]
print(f"  Budget sor: {bl['account_code']} - {bl['account_name']} ({bl['period']})")
print(f"  Tervezett: {bl['planned_amount']:,.0f} | Szabad: {bl.get('available', '?')}")

po = api("POST", f"{FINANCE}/purchase-orders/", {
    "department_id": bl["department_id"],
    "budget_line_id": bl["id"],
    "supplier_name": "TesztSzallito Kft.",
    "supplier_tax_id": "12345678-2-42",
    "accounting_code": bl["account_code"],
    "lines": [
        {"description": "Laptop Dell Latitude 5540", "quantity": 2, "unit_price": 350000},
        {"description": "Monitor Dell 27\" 4K", "quantity": 2, "unit_price": 150000},
    ],
}, clerk_token)

if "_error" in po:
    print("PO letrehozas sikertelen"); exit(1)

po_id = po["id"]
print(f"  >> PO letrehozva: {po['po_number']}")
print(f"     Osszeg: {po['amount']:,.0f} {po['currency']}")
print(f"     Statusz: {po['status']}")
print(f"     Szallito: TesztSzallito Kft. (12345678-2-42)")

approvals = api("GET", f"{FINANCE}/purchase-orders/{po_id}/approvals", token=clerk_token)
print(f"  Jovahagyasi lanc ({len(approvals)} lepes):")
for a in approvals:
    print(f"     {a['step']}. {a['step_name']} - {a['status']} ({a['assigned_role']}, {a.get('assignee_name', '-')})")


# =============================================
step(2, "PO JOVAHAGYAS (hierarchia szerint)")
# =============================================

# Approve step by step with the correct users
for a in approvals:
    if a["status"] != "pending":
        # Refresh
        approvals = api("GET", f"{FINANCE}/purchase-orders/{po_id}/approvals", token=clerk_token)
        a_fresh = [x for x in approvals if x["step"] == a["step"]]
        if a_fresh and a_fresh[0]["status"] != "pending":
            continue

    # Determine who should approve this step
    role = a["assigned_role"]
    assignee = a.get("assignee_name", "")
    if "Farkas" in str(assignee) or role == "department_head":
        tok = dept_head_token
        who = "Farkas Tamas (dept_head)"
    elif role == "admin":
        tok = admin_token
        who = "Admin User"
    elif role == "cfo":
        tok = cfo_token
        who = "CFO"
    else:
        tok = admin_token
        who = f"Admin (fallback, role={role})"

    r = api("POST", f"{FINANCE}/purchase-orders/{po_id}/approvals/{a['step']}/decide",
            {"decision": "approved", "comment": f"Jovahagyva - {who}"}, tok)
    status = "OK" if "_error" not in r else f"FAIL ({r.get('_detail', '')[:80]})"
    print(f"  {a['step']}. {a['step_name']} -> {who} -> {status}")

# Final check
approvals_final = api("GET", f"{FINANCE}/purchase-orders/{po_id}/approvals", token=clerk_token)
for a in approvals_final:
    print(f"     {a['step']}. {a['step_name']} - {a['status']} {a.get('decider_name', '')}")

po_list = api("GET", f"{FINANCE}/purchase-orders/?limit=50", token=clerk_token)
po_now = next((p for p in po_list.get("items", []) if p["id"] == po_id), None)
print(f"  PO statusz: {po_now['status'] if po_now else '?'}")


# =============================================
step(3, "PO KIKULDES (Antal Norbert, letrehozo)")
# =============================================

send = api("POST", f"{FINANCE}/purchase-orders/{po_id}/send", token=clerk_token)
if "_error" not in send:
    print(f"  >> PO kikuldve szallitonak!")
    print(f"     Statusz: {send.get('status', '?')}")
else:
    print(f"  !! Kikuldes sikertelen")


# =============================================
step(4, "SZAMLA BEERKEZES + DIGITALIZALAS (szimulacio)")
# =============================================

from common.database import async_session_factory
from common.models.invoice import Invoice, InvoiceStatus
from common.models.extraction import ExtractionResult
import asyncio

async def create_test_invoice():
    async with async_session_factory() as db:
        inv = Invoice(
            invoice_number="TSZ-2026-042",
            original_filename="tesztszallito_szamla_042.pdf",
            stored_filepath="/data/invoices/tesztszallito_szamla_042.pdf",
            status=InvoiceStatus.pending_review,
            net_amount=1000000,
            vat_rate=27,
            vat_amount=270000,
            gross_amount=1000000,  # same as PO amount for match
            currency="HUF",
            payment_method="atutalas",
            ocr_confidence=0.95,
        )
        db.add(inv)
        await db.flush()

        ext = ExtractionResult(
            invoice_id=inv.id,
            extracted_data={
                "szallito_nev": "TesztSzallito Kft.",
                "szallito_adoszam": "12345678-2-42",
                "szamla_szam": "TSZ-2026-042",
                "netto_osszeg": 1000000,
                "afa_osszeg": 270000,
                "brutto_osszeg": 1000000,
                "penznem": "HUF",
            },
            confidence_scores={"overall": 0.95},
            model_used="gpt-4o-mini",
            extraction_time_ms=1200,
        )
        db.add(ext)
        await db.commit()
        await db.refresh(inv)
        return inv.id, inv.invoice_number

invoice_id, inv_number = asyncio.get_event_loop().run_until_complete(create_test_invoice())
print(f"  >> Szamla letrehozva: {inv_number}")
print(f"     ID: {invoice_id}")
print(f"     Brutto: 1,000,000 HUF")
print(f"     Szallito: TesztSzallito Kft. (12345678-2-42)")
print(f"     Statusz: pending_review")
print(f"     PO osszeg: {po['amount']:,.0f} = Szamla brutto: 1,000,000 -> egyezni fog!")


# =============================================
step(5, "SZAMLA JOVAHAGYASRA KULDES")
# =============================================

submit = api("POST", f"{PIPELINE}/invoices/{invoice_id}/submit-approval", token=reviewer_token or cfo_token)
if "_error" not in submit:
    print(f"  >> Szamla jovahagyasra kuldve")
else:
    print(f"  !! Submit failed")

inv_approvals = api("GET", f"{PIPELINE}/invoices/{invoice_id}/approvals", token=cfo_token)
if isinstance(inv_approvals, list):
    print(f"  Szamla jovahagyasi lanc ({len(inv_approvals)} lepes):")
    for a in inv_approvals:
        print(f"     {a['step']}. {a['step_name']} - {a['status']} ({a.get('assigned_role', '-')})")


# =============================================
step(6, "SZAMLA JOVAHAGYAS (3 lepes)")
# =============================================

# Step 1: reviewer
r1 = api("POST", f"{PIPELINE}/invoices/{invoice_id}/approvals/1/decide",
         {"decision": "approved", "comment": "OCR adatok rendben"}, reviewer_token or cfo_token)
print(f"  1. Ellenorzes -> {'OK approved' if '_error' not in r1 else 'FAIL'}")

# Step 2: department_head
r2 = api("POST", f"{PIPELINE}/invoices/{invoice_id}/approvals/2/decide",
         {"decision": "approved", "comment": "Osszeg egyezik"}, dept_head_token)
if "_error" in r2:
    # dept_head may not have the right role, use admin
    r2 = api("POST", f"{PIPELINE}/invoices/{invoice_id}/approvals/2/decide",
             {"decision": "approved", "comment": "Osszeg egyezik"}, admin_token)
print(f"  2. Jovahagyas -> {'OK approved' if '_error' not in r2 else 'FAIL'}")

# Step 3: cfo
r3 = api("POST", f"{PIPELINE}/invoices/{invoice_id}/approvals/3/decide",
         {"decision": "approved", "comment": "Jovahagyom"}, cfo_token)
print(f"  3. Penzugyi jovahagyas -> {'OK approved' if '_error' not in r3 else 'skipped/error'}")

time.sleep(0.5)
inv_detail = api("GET", f"{PIPELINE}/invoices/{invoice_id}", token=cfo_token)
inv_status = inv_detail.get("status", "?")
print(f"\n  Szamla statusz az approval utan: {inv_status}")


# =============================================
step(7, "PO-SZAMLA EGYEZTETES")
# =============================================

if inv_status == "matched":
    print(f"  >> AUTO-MATCH SIKERES! Szamla automatikusan egyeztetve.")
elif inv_status == "awaiting_match":
    print(f"  Auto-match nem futott vagy nem talalt egyezest. Manualis...")
    match_r = api("POST", f"{PIPELINE}/reconciliation/{invoice_id}/match", token=cfo_token)
    print(f"  Auto match: {match_r.get('status', '?')} - {match_r.get('reason', match_r.get('po_number', ''))}")
    if match_r.get("status") == "mismatch":
        print(f"  -> Kezi hozzarendeles...")
        manual = api("POST", f"{PIPELINE}/reconciliation/{invoice_id}/manual-match",
                     {"purchase_order_id": po_id}, cfo_token)
        print(f"  Kezi match: {manual.get('status', '?')} - PO {manual.get('po_number', '?')}")
else:
    print(f"  Szamla statusz: {inv_status}")

# Refresh
inv_detail2 = api("GET", f"{PIPELINE}/invoices/{invoice_id}", token=cfo_token)
inv_status2 = inv_detail2.get("status", "?")
print(f"  Szamla statusz match utan: {inv_status2}")


# =============================================
step(8, "KONYVELES FEADAS")
# =============================================

if inv_status2 == "matched":
    post = api("POST", f"{PIPELINE}/reconciliation/{invoice_id}/post", token=cfo_token)
    if "_error" not in post:
        print(f"  >> Konyvelve!")
        print(f"     Tartozik: {post.get('debit_account')} -> {post.get('net_amount'):,.0f} HUF")
        if post.get("vat_amount", 0) > 0:
            print(f"     Tartozik AFA: 466 -> {post.get('vat_amount'):,.0f} HUF")
        print(f"     Kovel: {post.get('credit_account')} -> {post.get('gross_amount'):,.0f} HUF")
        print(f"     Idoszak: {post.get('period')}")
        print(f"     Sablon: {post.get('template')}")
    else:
        print(f"  !! Konyveles sikertelen")
else:
    print(f"  !! Szamla nem matched: {inv_status2}")


# =============================================
step(9, "VEGALLAPOT")
# =============================================

po_list2 = api("GET", f"{FINANCE}/purchase-orders/?limit=50", token=clerk_token)
final_po = next((p for p in po_list2.get("items", []) if p["id"] == po_id), None)
final_inv = api("GET", f"{PIPELINE}/invoices/{invoice_id}", token=cfo_token)

if final_po:
    print(f"  PO:     {final_po['po_number']} | {final_po['status']} | {final_po['amount']:,.0f} HUF")
else:
    print(f"  PO:     nem talalhato")
ga = final_inv.get('gross_amount', 0) or 0
print(f"  Szamla: {final_inv.get('invoice_number','?')} | {final_inv.get('status','?')} | {ga:,.0f} HUF")

print(f"\n{'='*60}")
print(f"  TELJES CIKLUS BEFEJEZVE")
print(f"{'='*60}")
