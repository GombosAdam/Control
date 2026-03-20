"""Generate diverse invoices in multiple languages and layouts.
Languages: HU, EN, RU, SR, SK, HR, CZ, DE, FR, ES
Layouts: 5 different styles
"""
import random
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "inbox")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Find a Unicode font
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "C:\\Windows\\Fonts\\DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]

UNICODE_FONT = 'Helvetica'
UNICODE_FONT_BOLD = 'Helvetica-Bold'

for fp in FONT_PATHS:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('Unicode', fp))
            UNICODE_FONT = 'Unicode'
            bold_fp = fp.replace('Sans.ttf', 'Sans-Bold.ttf').replace('Regular', 'Bold')
            if os.path.exists(bold_fp):
                pdfmetrics.registerFont(TTFont('UnicodeBold', bold_fp))
                UNICODE_FONT_BOLD = 'UnicodeBold'
            else:
                UNICODE_FONT_BOLD = 'Unicode'
            print(f"Font: {fp}")
            break
        except:
            continue

# === COMPANY DATA ===
COMPANIES = {
    'hu': [
        ("Magyar Tech Kft.", "Budapest, Váci út 35, 1134", "12345678-2-41"),
        ("Innovatív Megoldások Zrt.", "Debrecen, Piac utca 20, 4025", "87654321-1-09"),
        ("Dunai Szolgáltatások Kft.", "Győr, Baross Gábor út 10, 9021", "11223344-2-08"),
        ("Pannon Rendszerek Bt.", "Pécs, Széchenyi tér 7, 7621", "55667788-1-02"),
        ("Alföldi Informatika Kft.", "Szeged, Kárász utca 5, 6720", "99887766-2-06"),
    ],
    'en': [
        ("TechCorp Solutions Ltd.", "123 Innovation Drive, San Francisco, CA 94102", "US12-345678901"),
        ("Global Trade Partners", "456 Commerce Street, New York, NY 10001", "US98-765432109"),
        ("Digital Services Inc.", "789 Tech Boulevard, Austin, TX 78701", "US55-123456789"),
        ("CloudNet Systems", "321 Data Center Way, Seattle, WA 98101", "US77-888999000"),
    ],
    'ru': [
        ("ООО ТехноСервис", "Москва, ул. Ленина 15, офис 203", "ИНН 7712345678"),
        ("АО Глобал Трейд", "Санкт-Петербург, Невский пр. 100", "ИНН 7823456789"),
        ("ЗАО СофтЛайн", "Новосибирск, ул. Красная 45", "ИНН 5412345678"),
        ("ИП Иванов А.П.", "Казань, ул. Баумана 33", "ИНН 1612345678"),
        ("ООО ДатаЦентр", "Екатеринбург, ул. Мира 78", "ИНН 6612345678"),
    ],
    'sr': [
        ("Техно Солуције д.о.о.", "Београд, Кнез Михаилова 22", "ПИБ 100123456"),
        ("Дигитал Сервис а.д.", "Нови Сад, Булевар ослобођења 15", "ПИБ 200234567"),
        ("ИТ Систем д.о.о.", "Ниш, Обреновићева 10", "ПИБ 300345678"),
        ("Балкан Трејд д.о.о.", "Крагујевац, Краља Петра 5", "ПИБ 400456789"),
    ],
    'sk': [
        ("TechSoft s.r.o.", "Bratislava, Obchodná 15, 811 06", "IČO 12345678"),
        ("Digitálne Služby a.s.", "Košice, Hlavná 20, 040 01", "IČO 23456789"),
        ("Inovatívne Riešenia s.r.o.", "Žilina, Námestie 8, 010 01", "IČO 34567890"),
        ("Stredné Systémy s.r.o.", "Banská Bystrica, SNP 12, 974 01", "IČO 45678901"),
    ],
    'hr': [
        ("Digital Rješenja d.o.o.", "Zagreb, Ilica 45, 10000", "OIB 12345678901"),
        ("Tech Partneri d.d.", "Split, Riva 10, 21000", "OIB 23456789012"),
        ("Adriatic Systems d.o.o.", "Rijeka, Korzo 15, 51000", "OIB 34567890123"),
        ("Jadranski IT d.o.o.", "Dubrovnik, Stradun 5, 20000", "OIB 45678901234"),
    ],
    'cz': [
        ("TechPro s.r.o.", "Praha, Václavské nám. 20, 110 00", "IČO 12345678"),
        ("Digitální Služby a.s.", "Brno, Masarykova 15, 602 00", "IČO 23456789"),
        ("Inovační Řešení s.r.o.", "Ostrava, Nádražní 10, 702 00", "IČO 34567890"),
        ("České Systémy s.r.o.", "Plzeň, Americká 5, 301 00", "IČO 45678901"),
    ],
    'de': [
        ("Schmidt & Partner GmbH", "Hauptstraße 45, 80331 München", "DE123456789"),
        ("TechWerk AG", "Industrieweg 12, 10115 Berlin", "DE987654321"),
        ("Müller Consulting", "Bahnhofstraße 78, 60311 Frankfurt", "DE456789123"),
    ],
    'fr': [
        ("Solutions Digitales SARL", "15 Rue de la Paix, 75001 Paris", "FR12345678901"),
        ("Tech Innovation SAS", "28 Avenue des Champs-Élysées, 75008 Paris", "FR98765432109"),
    ],
    'es': [
        ("Tecnología Avanzada S.L.", "Calle Gran Vía 45, 28013 Madrid", "ES-B12345678"),
        ("Servicios Digitales S.A.", "Paseo de Gracia 100, 08008 Barcelona", "ES-A87654321"),
    ],
}

# === ITEMS ===
ITEMS = {
    'hu': [
        ("Szoftverlicenc (éves)", 300000, 600000),
        ("Felhő szolgáltatás", 150000, 400000),
        ("Műszaki támogatás", 80000, 200000),
        ("IT tanácsadás", 50000, 150000),
        ("Hálózati berendezés", 100000, 500000),
        ("Adatbázis karbantartás", 60000, 180000),
    ],
    'en': [
        ("Software License (Annual)", 1200, 5000),
        ("Cloud Hosting Services", 500, 2000),
        ("Technical Support (Monthly)", 200, 800),
        ("Data Analytics Package", 800, 3000),
        ("Security Audit", 1500, 5000),
        ("API Integration", 300, 1200),
        ("Training Session", 500, 1500),
    ],
    'ru': [
        ("Лицензия на ПО (годовая)", 50000, 150000),
        ("Услуги хостинга", 20000, 80000),
        ("Техническая поддержка", 15000, 45000),
        ("Аналитика данных", 30000, 100000),
        ("Аудит безопасности", 60000, 200000),
        ("Разработка ПО", 80000, 300000),
    ],
    'sr': [
        ("Софтверска лиценца (годишња)", 50000, 150000),
        ("Хостинг услуге", 20000, 70000),
        ("Техничка подршка", 15000, 50000),
        ("ИТ консалтинг", 30000, 100000),
        ("Мрежна опрема", 40000, 120000),
        ("Безбедносни аудит", 50000, 180000),
    ],
    'sk': [
        ("Softvérová licencia (ročná)", 1000, 3000),
        ("Cloudové služby", 500, 2000),
        ("Technická podpora", 300, 1000),
        ("IT poradenstvo", 400, 1500),
        ("Sieťové zariadenia", 800, 3000),
        ("Údržba databázy", 200, 800),
    ],
    'hr': [
        ("Softverska licenca (godišnja)", 1000, 3000),
        ("Usluge hostinga", 500, 2000),
        ("Tehnička podrška", 300, 1000),
        ("IT savjetovanje", 400, 1500),
        ("Mrežna oprema", 800, 3000),
        ("Sigurnosni audit", 600, 2500),
    ],
    'cz': [
        ("Softwarová licence (roční)", 1000, 3000),
        ("Cloudové služby", 500, 2000),
        ("Technická podpora", 300, 1000),
        ("IT poradenství", 400, 1500),
        ("Síťové zařízení", 800, 3000),
        ("Údržba databáze", 200, 800),
    ],
    'de': [
        ("Softwarelizenz (Jährlich)", 1000, 3000),
        ("Cloud-Hosting-Dienste", 400, 1500),
        ("Technischer Support", 200, 600),
        ("Beratungsleistungen", 150, 400),
        ("Netzwerkausrüstung", 500, 2000),
    ],
    'fr': [
        ("Licence logicielle (Annuelle)", 1100, 1800),
        ("Services d'hébergement", 450, 1600),
        ("Support technique", 180, 550),
        ("Conseil informatique", 300, 1200),
    ],
    'es': [
        ("Licencia de software (Anual)", 900, 1600),
        ("Servicios de hosting", 350, 1400),
        ("Soporte técnico", 150, 450),
        ("Consultoría IT", 300, 1100),
    ],
}

# === LABELS ===
LABELS = {
    'hu': {
        'invoice': 'SZÁMLA', 'invoice_no': 'Számlaszám:', 'date': 'Kelt:',
        'due_date': 'Fizetési határidő:', 'from': 'Eladó:', 'to': 'Vevő:',
        'item': 'Megnevezés', 'qty': 'Menny.', 'price': 'Egységár', 'total': 'Összesen',
        'subtotal': 'Nettó:', 'tax': 'ÁFA (27%):', 'grand_total': 'BRUTTÓ:',
        'currency': 'HUF', 'bank': 'Bankszámlaszám:', 'thank_you': 'Köszönjük a vásárlást!',
        'tax_id': 'Adószám:', 'payment': 'Fizetési mód:', 'fulfillment': 'Teljesítés:',
    },
    'en': {
        'invoice': 'INVOICE', 'invoice_no': 'Invoice No:', 'date': 'Date:',
        'due_date': 'Due Date:', 'from': 'From:', 'to': 'Bill To:',
        'item': 'Description', 'qty': 'Qty', 'price': 'Unit Price', 'total': 'Total',
        'subtotal': 'Subtotal:', 'tax': 'Tax (20%):', 'grand_total': 'TOTAL:',
        'currency': 'USD', 'bank': 'Bank Account:', 'thank_you': 'Thank you for your business!',
        'tax_id': 'Tax ID:', 'payment': 'Payment Method:', 'fulfillment': 'Fulfillment:',
    },
    'ru': {
        'invoice': 'СЧЁТ-ФАКТУРА', 'invoice_no': 'Счёт №:', 'date': 'Дата:',
        'due_date': 'Срок оплаты:', 'from': 'Поставщик:', 'to': 'Покупатель:',
        'item': 'Наименование', 'qty': 'Кол-во', 'price': 'Цена', 'total': 'Сумма',
        'subtotal': 'Итого:', 'tax': 'НДС (20%):', 'grand_total': 'ВСЕГО:',
        'currency': 'RUB', 'bank': 'Расчётный счёт:', 'thank_you': 'Спасибо за сотрудничество!',
        'tax_id': 'ИНН:', 'payment': 'Способ оплаты:', 'fulfillment': 'Дата исполнения:',
    },
    'sr': {
        'invoice': 'ФАКТУРА', 'invoice_no': 'Број фактуре:', 'date': 'Датум:',
        'due_date': 'Рок плаћања:', 'from': 'Продавац:', 'to': 'Купац:',
        'item': 'Опис', 'qty': 'Кол.', 'price': 'Цена', 'total': 'Укупно',
        'subtotal': 'Подзбир:', 'tax': 'ПДВ (20%):', 'grand_total': 'УКУПНО:',
        'currency': 'RSD', 'bank': 'Жиро рачун:', 'thank_you': 'Хвала на сарадњи!',
        'tax_id': 'ПИБ:', 'payment': 'Начин плаћања:', 'fulfillment': 'Датум промета:',
    },
    'sk': {
        'invoice': 'FAKTÚRA', 'invoice_no': 'Číslo faktúry:', 'date': 'Dátum:',
        'due_date': 'Dátum splatnosti:', 'from': 'Dodávateľ:', 'to': 'Odberateľ:',
        'item': 'Popis', 'qty': 'Mn.', 'price': 'Jedn. cena', 'total': 'Celkom',
        'subtotal': 'Základ dane:', 'tax': 'DPH (20%):', 'grand_total': 'CELKOM:',
        'currency': 'EUR', 'bank': 'Bankový účet:', 'thank_you': 'Ďakujeme za spoluprácu!',
        'tax_id': 'IČO:', 'payment': 'Spôsob platby:', 'fulfillment': 'Dátum dodania:',
    },
    'hr': {
        'invoice': 'RAČUN', 'invoice_no': 'Broj računa:', 'date': 'Datum:',
        'due_date': 'Rok plaćanja:', 'from': 'Prodavatelj:', 'to': 'Kupac:',
        'item': 'Opis', 'qty': 'Kol.', 'price': 'Jed. cijena', 'total': 'Ukupno',
        'subtotal': 'Osnovica:', 'tax': 'PDV (25%):', 'grand_total': 'UKUPNO:',
        'currency': 'EUR', 'bank': 'IBAN:', 'thank_you': 'Hvala na suradnji!',
        'tax_id': 'OIB:', 'payment': 'Način plaćanja:', 'fulfillment': 'Datum isporuke:',
    },
    'cz': {
        'invoice': 'FAKTURA', 'invoice_no': 'Číslo faktury:', 'date': 'Datum:',
        'due_date': 'Datum splatnosti:', 'from': 'Dodavatel:', 'to': 'Odběratel:',
        'item': 'Popis', 'qty': 'Mn.', 'price': 'Jedn. cena', 'total': 'Celkem',
        'subtotal': 'Základ daně:', 'tax': 'DPH (21%):', 'grand_total': 'CELKEM:',
        'currency': 'CZK', 'bank': 'Bankovní účet:', 'thank_you': 'Děkujeme za spolupráci!',
        'tax_id': 'IČO:', 'payment': 'Způsob platby:', 'fulfillment': 'Datum dodání:',
    },
    'de': {
        'invoice': 'RECHNUNG', 'invoice_no': 'Rechnungs-Nr:', 'date': 'Datum:',
        'due_date': 'Fällig am:', 'from': 'Von:', 'to': 'An:',
        'item': 'Beschreibung', 'qty': 'Menge', 'price': 'Einzelpreis', 'total': 'Gesamt',
        'subtotal': 'Zwischensumme:', 'tax': 'MwSt (19%):', 'grand_total': 'GESAMTBETRAG:',
        'currency': 'EUR', 'bank': 'Bankverbindung:', 'thank_you': 'Vielen Dank für Ihren Auftrag!',
        'tax_id': 'USt-IdNr:', 'payment': 'Zahlungsart:', 'fulfillment': 'Lieferdatum:',
    },
    'fr': {
        'invoice': 'FACTURE', 'invoice_no': 'Facture N°:', 'date': 'Date:',
        'due_date': 'Échéance:', 'from': 'De:', 'to': 'À:',
        'item': 'Description', 'qty': 'Qté', 'price': 'Prix unitaire', 'total': 'Total',
        'subtotal': 'Sous-total:', 'tax': 'TVA (20%):', 'grand_total': 'TOTAL TTC:',
        'currency': 'EUR', 'bank': 'Coordonnées bancaires:', 'thank_you': 'Merci pour votre confiance!',
        'tax_id': 'SIRET:', 'payment': 'Mode de paiement:', 'fulfillment': 'Date de livraison:',
    },
    'es': {
        'invoice': 'FACTURA', 'invoice_no': 'Factura Nº:', 'date': 'Fecha:',
        'due_date': 'Vencimiento:', 'from': 'De:', 'to': 'Para:',
        'item': 'Descripción', 'qty': 'Cant.', 'price': 'Precio', 'total': 'Total',
        'subtotal': 'Subtotal:', 'tax': 'IVA (21%):', 'grand_total': 'TOTAL:',
        'currency': 'EUR', 'bank': 'Datos bancarios:', 'thank_you': '¡Gracias por su confianza!',
        'tax_id': 'CIF:', 'payment': 'Forma de pago:', 'fulfillment': 'Fecha de entrega:',
    },
}

TAX_RATES = {
    'hu': 0.27, 'en': 0.20, 'ru': 0.20, 'sr': 0.20, 'sk': 0.20,
    'hr': 0.25, 'cz': 0.21, 'de': 0.19, 'fr': 0.20, 'es': 0.21,
}

PAYMENT_METHODS = {
    'hu': ['Átutalás', 'Készpénz', 'Bankkártya'],
    'en': ['Bank Transfer', 'Cash', 'Credit Card'],
    'ru': ['Банковский перевод', 'Наличные', 'Карта'],
    'sr': ['Вирман', 'Готовина', 'Картица'],
    'sk': ['Prevod', 'Hotovosť', 'Karta'],
    'hr': ['Virman', 'Gotovina', 'Kartica'],
    'cz': ['Převod', 'Hotovost', 'Karta'],
    'de': ['Überweisung', 'Bargeld', 'Karte'],
    'fr': ['Virement', 'Espèces', 'Carte'],
    'es': ['Transferencia', 'Efectivo', 'Tarjeta'],
}

def random_date(start_year=2023, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 3, 20)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def random_iban(country='HU'):
    codes = {'HU': 'HU42', 'RU': 'RU00', 'RS': 'RS35', 'SK': 'SK31', 'HR': 'HR12',
             'CZ': 'CZ65', 'DE': 'DE89', 'FR': 'FR76', 'ES': 'ES91', 'US': 'US00'}
    prefix = codes.get(country, 'XX00')
    return f"{prefix} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"


# ============================================================
# 5 DIFFERENT LAYOUTS
# ============================================================

def layout_classic(c, lang, inv_num, width, height):
    """Layout 1: Classic - header top left, details below."""
    labels = LABELS[lang]
    company = random.choice(COMPANIES[lang])
    buyer = random.choice(COMPANIES[random.choice(list(COMPANIES.keys()))])
    inv_date = random_date()

    c.setFont(UNICODE_FONT_BOLD, 24)
    c.drawString(50, height - 50, labels['invoice'])

    c.setFont(UNICODE_FONT, 10)
    c.drawString(50, height - 80, f"{labels['invoice_no']} INV-{inv_num:05d}")
    c.drawString(50, height - 95, f"{labels['date']} {inv_date.strftime('%Y-%m-%d')}")
    c.drawString(50, height - 110, f"{labels['due_date']} {(inv_date + timedelta(days=30)).strftime('%Y-%m-%d')}")
    c.drawString(50, height - 125, f"{labels['payment']} {random.choice(PAYMENT_METHODS[lang])}")

    c.setFont(UNICODE_FONT_BOLD, 10)
    c.drawString(50, height - 160, labels['from'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 175, company[0])
    c.drawString(50, height - 188, company[1])
    c.drawString(50, height - 201, f"{labels['tax_id']} {company[2]}")

    c.setFont(UNICODE_FONT_BOLD, 10)
    c.drawString(300, height - 160, labels['to'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(300, height - 175, buyer[0])
    c.drawString(300, height - 188, buyer[1])

    return height - 260, company, buyer, inv_date

def layout_right_header(c, lang, inv_num, width, height):
    """Layout 2: Company left, invoice title right."""
    labels = LABELS[lang]
    company = random.choice(COMPANIES[lang])
    buyer = random.choice(COMPANIES[random.choice(list(COMPANIES.keys()))])
    inv_date = random_date()

    c.setFont(UNICODE_FONT_BOLD, 14)
    c.drawString(50, height - 50, company[0])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 65, company[1])
    c.drawString(50, height - 78, f"{labels['tax_id']} {company[2]}")

    c.setFont(UNICODE_FONT_BOLD, 28)
    c.drawRightString(width - 50, height - 50, labels['invoice'])
    c.setFont(UNICODE_FONT, 10)
    c.drawRightString(width - 50, height - 75, f"{labels['invoice_no']} {inv_num:06d}")
    c.drawRightString(width - 50, height - 90, f"{labels['date']} {inv_date.strftime('%d.%m.%Y')}")
    c.drawRightString(width - 50, height - 105, f"{labels['due_date']} {(inv_date + timedelta(days=14)).strftime('%d.%m.%Y')}")

    c.setFont(UNICODE_FONT_BOLD, 10)
    c.drawString(50, height - 130, labels['to'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 145, buyer[0])
    c.drawString(50, height - 158, buyer[1])

    return height - 210, company, buyer, inv_date

def layout_centered_boxes(c, lang, inv_num, width, height):
    """Layout 3: Centered title, boxed seller/buyer."""
    labels = LABELS[lang]
    company = random.choice(COMPANIES[lang])
    buyer = random.choice(COMPANIES[random.choice(list(COMPANIES.keys()))])
    inv_date = random_date()

    c.setFont(UNICODE_FONT_BOLD, 30)
    c.drawCentredString(width/2, height - 55, labels['invoice'])
    c.setFont(UNICODE_FONT, 11)
    c.drawCentredString(width/2, height - 78, f"# {inv_num:07d}")
    c.drawCentredString(width/2, height - 95, f"{labels['date']} {inv_date.strftime('%Y/%m/%d')}")

    # Boxes
    c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
    c.setLineWidth(0.5)
    c.rect(40, height - 200, 240, 80)
    c.rect(width - 280, height - 200, 240, 80)

    c.setFont(UNICODE_FONT_BOLD, 9)
    c.drawString(50, height - 132, labels['from'])
    c.setFont(UNICODE_FONT, 8)
    c.drawString(50, height - 147, company[0])
    c.drawString(50, height - 160, company[1])
    c.drawString(50, height - 173, f"{labels['tax_id']} {company[2]}")

    c.setFont(UNICODE_FONT_BOLD, 9)
    c.drawString(width - 270, height - 132, labels['to'])
    c.setFont(UNICODE_FONT, 8)
    c.drawString(width - 270, height - 147, buyer[0])
    c.drawString(width - 270, height - 160, buyer[1])

    return height - 250, company, buyer, inv_date

def layout_stripe_header(c, lang, inv_num, width, height):
    """Layout 4: Dark stripe header with white text."""
    labels = LABELS[lang]
    company = random.choice(COMPANIES[lang])
    buyer = random.choice(COMPANIES[random.choice(list(COMPANIES.keys()))])
    inv_date = random_date()

    # Dark header stripe
    accent = random.choice([
        colors.Color(0.15, 0.2, 0.35),
        colors.Color(0.1, 0.3, 0.2),
        colors.Color(0.3, 0.15, 0.15),
        colors.Color(0.2, 0.2, 0.2),
    ])
    c.setFillColor(accent)
    c.rect(0, height - 90, width, 90, fill=True)

    c.setFillColor(colors.white)
    c.setFont(UNICODE_FONT_BOLD, 26)
    c.drawString(50, height - 45, labels['invoice'])
    c.setFont(UNICODE_FONT, 11)
    c.drawRightString(width - 50, height - 35, f"{labels['invoice_no']} {inv_num:05d}")
    c.drawRightString(width - 50, height - 55, f"{labels['date']} {inv_date.strftime('%Y-%m-%d')}")
    c.drawRightString(width - 50, height - 75, f"{labels['due_date']} {(inv_date + timedelta(days=45)).strftime('%Y-%m-%d')}")

    c.setFillColor(colors.black)

    # Seller / Buyer side by side
    c.setFont(UNICODE_FONT_BOLD, 10)
    c.drawString(50, height - 120, labels['from'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 135, company[0])
    c.drawString(50, height - 148, company[1])
    c.drawString(50, height - 161, f"{labels['tax_id']} {company[2]}")

    c.setFont(UNICODE_FONT_BOLD, 10)
    c.drawString(width/2 + 20, height - 120, labels['to'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(width/2 + 20, height - 135, buyer[0])
    c.drawString(width/2 + 20, height - 148, buyer[1])

    return height - 210, company, buyer, inv_date

def layout_minimal(c, lang, inv_num, width, height):
    """Layout 5: Minimalist - thin line, sparse."""
    labels = LABELS[lang]
    company = random.choice(COMPANIES[lang])
    buyer = random.choice(COMPANIES[random.choice(list(COMPANIES.keys()))])
    inv_date = random_date()

    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 30, company[0])
    c.drawString(50, height - 42, company[1])

    c.setFont(UNICODE_FONT_BOLD, 18)
    c.drawRightString(width - 50, height - 30, labels['invoice'])

    # Thin line
    c.setStrokeColor(colors.Color(0.85, 0.85, 0.85))
    c.setLineWidth(1)
    c.line(50, height - 55, width - 50, height - 55)

    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 75, f"{labels['invoice_no']} {inv_num}")
    c.drawString(200, height - 75, f"{labels['date']} {inv_date.strftime('%d/%m/%Y')}")
    c.drawString(350, height - 75, f"{labels['due_date']} {(inv_date + timedelta(days=random.choice([7,14,30,60]))).strftime('%d/%m/%Y')}")

    c.setFont(UNICODE_FONT_BOLD, 9)
    c.drawString(50, height - 105, labels['to'])
    c.setFont(UNICODE_FONT, 9)
    c.drawString(50, height - 118, buyer[0])
    c.drawString(50, height - 131, buyer[1])

    return height - 175, company, buyer, inv_date

LAYOUTS = [layout_classic, layout_right_header, layout_centered_boxes, layout_stripe_header, layout_minimal]


def draw_items_table(c, lang, y_start, width):
    """Draw items table."""
    labels = LABELS[lang]
    items_list = ITEMS.get(lang, ITEMS['en'])
    tax_rate = TAX_RATES.get(lang, 0.20)

    # Table header
    header_color = random.choice([
        colors.Color(0.2, 0.2, 0.3),
        colors.Color(0.15, 0.35, 0.25),
        colors.Color(0.3, 0.2, 0.15),
        colors.Color(0.25, 0.25, 0.25),
    ])
    c.setFillColor(header_color)
    c.rect(40, y_start, width - 80, 20, fill=True)
    c.setFillColor(colors.white)
    c.setFont(UNICODE_FONT_BOLD, 8)
    c.drawString(50, y_start + 6, labels['item'])
    c.drawString(width - 210, y_start + 6, labels['qty'])
    c.drawString(width - 160, y_start + 6, labels['price'])
    c.drawString(width - 90, y_start + 6, labels['total'])

    c.setFillColor(colors.black)
    c.setFont(UNICODE_FONT, 9)
    y = y_start - 20
    subtotal = 0

    num_items = random.randint(2, 6)
    selected = random.sample(items_list, min(num_items, len(items_list)))

    for i, (item_name, min_p, max_p) in enumerate(selected):
        qty = random.randint(1, 10)
        price = random.randint(min_p, max_p)
        total = qty * price
        subtotal += total

        # Alternating row bg
        if i % 2 == 1:
            c.setFillColor(colors.Color(0.96, 0.96, 0.96))
            c.rect(40, y - 4, width - 80, 18, fill=True)
            c.setFillColor(colors.black)

        c.setFont(UNICODE_FONT, 9)
        c.drawString(50, y, item_name[:42])
        c.drawString(width - 210, y, str(qty))
        c.drawString(width - 160, y, f"{price:,.0f}")
        c.drawRightString(width - 50, y, f"{total:,.0f}")
        y -= 18

    y -= 15
    c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
    c.line(width - 220, y + 12, width - 40, y + 12)

    tax = subtotal * tax_rate
    grand_total = subtotal + tax

    c.setFont(UNICODE_FONT, 10)
    c.drawString(width - 220, y, labels['subtotal'])
    c.drawRightString(width - 50, y, f"{subtotal:,.0f} {labels['currency']}")

    y -= 18
    c.drawString(width - 220, y, labels['tax'])
    c.drawRightString(width - 50, y, f"{tax:,.0f} {labels['currency']}")

    y -= 22
    c.setFont(UNICODE_FONT_BOLD, 12)
    c.drawString(width - 220, y, labels['grand_total'])
    c.drawRightString(width - 50, y, f"{grand_total:,.0f} {labels['currency']}")

    return y, grand_total


def generate_invoice(inv_num, lang=None):
    """Generate a single invoice."""
    if lang is None:
        lang = random.choice(list(LABELS.keys()))
    layout_fn = random.choice(LAYOUTS)
    pagesize = random.choice([A4, LETTER])
    width, height = pagesize

    lang_codes = {'hu': 'HU', 'en': 'EN', 'ru': 'RU', 'sr': 'SR', 'sk': 'SK',
                  'hr': 'HR', 'cz': 'CZ', 'de': 'DE', 'fr': 'FR', 'es': 'ES'}
    filename = f"invoice_{lang_codes.get(lang, lang)}_{inv_num:04d}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=pagesize)
    y_start, company, buyer, inv_date = layout_fn(c, lang, inv_num, width, height)

    y_end, total = draw_items_table(c, lang, y_start, width)

    # Footer
    labels = LABELS[lang]
    country_map = {'hu': 'HU', 'de': 'DE', 'fr': 'FR', 'es': 'ES', 'sk': 'SK',
                   'hr': 'HR', 'cz': 'CZ', 'ru': 'RU', 'sr': 'RS', 'en': 'US'}
    c.setFont(UNICODE_FONT, 8)
    c.drawString(50, 55, labels['thank_you'])
    c.drawString(50, 42, f"{labels['bank']} {random_iban(country_map.get(lang, 'HU'))}")

    c.save()
    return filename, lang


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 200

    # Weight distribution: more RU, SR, SK, HR, CZ
    weighted_langs = ['ru'] * 25 + ['sr'] * 20 + ['sk'] * 15 + ['hr'] * 15 + ['cz'] * 15 + ['hu'] * 5 + ['en'] * 2 + ['de'] * 1 + ['fr'] * 1 + ['es'] * 1

    print(f"Generating {count} invoices to {OUTPUT_DIR}...")
    stats = {}
    for i in range(1, count + 1):
        lang = random.choice(weighted_langs)
        fname, actual_lang = generate_invoice(2000 + i, lang)
        stats[actual_lang] = stats.get(actual_lang, 0) + 1
        if i % 50 == 0:
            print(f"  {i}/{count}...")

    print(f"\nDone! Generated {count} invoices:")
    for lang, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {lang}: {cnt}")
