"""
Semantic schema for Arctic Text2SQL model.
DDL format + business rules + few-shot examples.
"""

DDL_SCHEMA = """
CREATE TABLE departments (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- osztaly neve
    code VARCHAR(20) UNIQUE NOT NULL,        -- osztaly kodja (pl. 'IT', 'FIN')
    parent_id VARCHAR(36) REFERENCES departments(id),  -- szulo osztaly
    manager_id VARCHAR(36) REFERENCES users(id),       -- osztalyvezeto
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin','cfo','department_head','accountant','reviewer')),
    department_id VARCHAR(36) REFERENCES departments(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_login TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE partners (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- partner neve (szallito/vevo)
    tax_number VARCHAR(20) UNIQUE,           -- adoszam
    bank_account VARCHAR(50),
    partner_type VARCHAR(10) NOT NULL CHECK (partner_type IN ('supplier','customer','both')),
    address VARCHAR(500),
    contact_email VARCHAR(255),
    auto_detected BOOLEAN DEFAULT FALSE NOT NULL,
    invoice_count INTEGER DEFAULT 0 NOT NULL,
    total_amount FLOAT DEFAULT 0.0 NOT NULL,
    vector_id VARCHAR(100),
    default_accounting_code VARCHAR(20),     -- tanult alapertelmezett konyviteli kod
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE scenarios (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,              -- szcenario neve
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    created_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE budget_lines (
    id VARCHAR(36) PRIMARY KEY,
    department_id VARCHAR(36) REFERENCES departments(id) NOT NULL,
    account_code VARCHAR(20) NOT NULL,       -- fokoenyvi szamla kod
    account_name VARCHAR(255) NOT NULL,
    period VARCHAR(7) NOT NULL,              -- idoszak, formatum: 'YYYY-MM'
    planned_amount FLOAT NOT NULL,           -- tervezett osszeg
    currency VARCHAR(3) DEFAULT 'HUF' NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('draft','approved','locked')),
    pnl_category VARCHAR(20) DEFAULT 'opex' NOT NULL CHECK (pnl_category IN ('revenue','cogs','opex','depreciation','interest','tax')),
    sort_order INTEGER DEFAULT 0 NOT NULL,
    plan_type VARCHAR(8) DEFAULT 'budget' NOT NULL CHECK (plan_type IN ('budget','forecast')),
    scenario_id VARCHAR(36) REFERENCES scenarios(id),
    created_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    approved_by VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE purchase_orders (
    id VARCHAR(36) PRIMARY KEY,
    po_number VARCHAR(50) UNIQUE NOT NULL,   -- megrendeles szam
    department_id VARCHAR(36) REFERENCES departments(id) NOT NULL,
    budget_line_id VARCHAR(36) REFERENCES budget_lines(id) NOT NULL,
    supplier_name VARCHAR(255) NOT NULL,
    supplier_tax_id VARCHAR(20),
    amount FLOAT NOT NULL,                   -- osszeg
    currency VARCHAR(3) DEFAULT 'HUF' NOT NULL,
    accounting_code VARCHAR(20) NOT NULL,
    description TEXT,
    status VARCHAR(15) NOT NULL CHECK (status IN ('draft','approved','received','closed','cancelled')),
    created_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    approved_by VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE invoices (
    id VARCHAR(36) PRIMARY KEY,
    invoice_number VARCHAR(100),             -- szamlaszam
    partner_id VARCHAR(36) REFERENCES partners(id),
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','ocr_processing','ocr_done','extracting','pending_review','in_approval','approved','awaiting_match','matched','posted','rejected','error')),
    invoice_date DATE,
    fulfillment_date DATE,                   -- teljesites datuma
    due_date DATE,                           -- fizetesi hatarido
    payment_method VARCHAR(50),
    net_amount FLOAT,                        -- netto osszeg
    vat_rate FLOAT,                          -- AFA kulcs
    vat_amount FLOAT,                        -- AFA osszeg
    gross_amount FLOAT,                      -- brutto osszeg
    currency VARCHAR(3) DEFAULT 'HUF' NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    is_duplicate BOOLEAN DEFAULT FALSE NOT NULL,
    purchase_order_id VARCHAR(36) REFERENCES purchase_orders(id),
    match_status VARCHAR(20) DEFAULT 'unmatched' NOT NULL,
    accounting_code VARCHAR(20),
    suggested_accounting_code VARCHAR(20),    -- AI-javasolt konyviteli kod
    anomaly_flags JSON,                      -- AI anomalia flagek
    ai_confidence FLOAT,                     -- AI osszetett confidence (0-1)
    reviewed_by_id VARCHAR(36) REFERENCES users(id),
    uploaded_by_id VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    approved_at TIMESTAMP
);

CREATE TABLE invoice_lines (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) REFERENCES invoices(id) ON DELETE CASCADE NOT NULL,
    description VARCHAR(500),                -- tetel leirasa
    quantity FLOAT,
    unit_price FLOAT,                        -- egysegar
    net_amount FLOAT,
    vat_rate FLOAT,
    vat_amount FLOAT,
    gross_amount FLOAT,
    sort_order INTEGER DEFAULT 0 NOT NULL
);

CREATE TABLE accounting_entries (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) REFERENCES invoices(id) NOT NULL,
    purchase_order_id VARCHAR(36) REFERENCES purchase_orders(id),
    account_code VARCHAR(20) NOT NULL,       -- fokoenyvi szamla
    department_id VARCHAR(36) REFERENCES departments(id) NOT NULL,
    amount FLOAT NOT NULL,                   -- osszeg
    currency VARCHAR(3) DEFAULT 'HUF' NOT NULL,
    period VARCHAR(7) NOT NULL,              -- idoszak 'YYYY-MM'
    entry_type VARCHAR(10) NOT NULL CHECK (entry_type IN ('debit','credit')),
    posted_at TIMESTAMP NOT NULL,
    posted_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE invoice_approvals (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) REFERENCES invoices(id) NOT NULL,
    step INTEGER NOT NULL,                   -- lepes szam (1=review, 2=approve, 3=final)
    step_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending','approved','rejected')),
    assigned_role VARCHAR(20) NOT NULL,
    decided_by VARCHAR(36) REFERENCES users(id),
    decided_at TIMESTAMP,
    comment TEXT,
    created_at TIMESTAMP
);

CREATE TABLE purchase_order_approvals (
    id VARCHAR(36) PRIMARY KEY,
    purchase_order_id VARCHAR(36) REFERENCES purchase_orders(id) NOT NULL,
    step INTEGER NOT NULL,
    step_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending','approved','rejected')),
    assigned_role VARCHAR(20) NOT NULL,
    decided_by VARCHAR(36) REFERENCES users(id),
    decided_at TIMESTAMP,
    comment TEXT,
    created_at TIMESTAMP
);

CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(36),
    details JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP
);

CREATE TABLE ai_enrichments (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) REFERENCES invoices(id) ON DELETE CASCADE NOT NULL,
    enrichment_type VARCHAR(50) NOT NULL,        -- partner_detection, duplicate_check, budget_suggestion, po_suggestion, anomaly_detection
    result_data JSON,
    confidence FLOAT,
    accepted BOOLEAN,                            -- NULL=pending, TRUE=elfogadva, FALSE=elutasitva
    created_at TIMESTAMP
);

CREATE TABLE cfo_metrics (
    id VARCHAR(36) PRIMARY KEY,
    metric_key VARCHAR(80) NOT NULL,             -- metrika azonosito
    period VARCHAR(7) NOT NULL,                  -- idoszak 'YYYY-MM'
    value FLOAT NOT NULL,                        -- szamitott ertek
    currency VARCHAR(3) DEFAULT 'HUF' NOT NULL,
    calculated_at TIMESTAMP NOT NULL,
    UNIQUE(metric_key, period)
);
-- cfo_metrics tartalma: elokalkulalt CFO metrikak (46 db, oranként frissul)
-- Hasznald a cfo_metrics tablat ha penzugyi osszesitesrol, KPI-rol, trendrol kerdeznek!
-- Metric kulcsok: invoice_total_count, invoice_processed_count, invoice_unprocessed_count,
--   invoice_rejected_count, invoice_total_gross_amount, invoice_processed_gross_amount,
--   budget_planned_total, budget_actual_total, budget_variance, budget_overage_line_count,
--   overdue_invoice_count, overdue_invoice_amount, upcoming_due_7d_amount, upcoming_due_30d_amount,
--   top_supplier_amount, active_supplier_count, supplier_concentration_top5_pct, avg_invoice_amount,
--   avg_processing_time_hours, avg_approval_time_hours, duplicate_invoice_count, error_rate_pct,
--   pnl_revenue, pnl_ebitda, pnl_net_income, dept_highest_spend_amount, dept_count_over_budget,
--   po_open_count, po_open_amount, invoice_amount_mom_change_pct,
--   forecast_cash_in_30d, forecast_cash_in_60d, forecast_cash_in_90d,
--   forecast_cash_out_30d, forecast_cash_out_60d, forecast_cash_out_90d,
--   forecast_net_cash_30d, forecast_net_cash_60d, forecast_net_cash_90d,
--   revenue_yoy_change_pct, expense_yoy_change_pct, ebitda_yoy_change_pct,
--   invoice_count_yoy_change_pct,
--   avg_payment_days, supplier_dependency_risk_count, supplier_price_trend_pct
""".strip()

BUSINESS_RULES = """
-- "Feldolgozott szamla" = invoices WHERE status IN ('approved','in_approval','awaiting_match','matched','posted','pending_review')
-- "Feldolgozatlan szamla" = invoices WHERE status IN ('uploaded','ocr_processing','ocr_done','extracting')
-- "Elutasitott szamla" = invoices WHERE status = 'rejected'
-- "Hibas szamla" = invoices WHERE status = 'error'
-- Osszeg lekerdezeseknel MINDIG szurj feldolgozott szamlakra: WHERE gross_amount IS NOT NULL
-- Ha a felhasznalo "szamlak"-rol kerdez osszeg nelkul, az OSSZES szamlat jelenti (nincs status szures)
-- Budget tullepes: budget_lines.planned_amount vs SUM(accounting_entries.amount) GROUP BY department_id + period
-- Period formatum: 'YYYY-MM', currency default: HUF
-- Partnerek = szallitok es/vagy vevok (partners tabla)
-- Jovahagyasra varo szamla: invoices WHERE status = 'in_approval'
-- Lejart hatarideju szamla: invoices WHERE due_date < CURRENT_DATE AND status NOT IN ('posted','rejected','error')
-- Mindig LIMIT 100, kiveve ha a felhasznalo mast ker (pl. TOP 5 → LIMIT 5)
-- Osszegeket ne kerekitsd, hasznald a pontos ertekeket
-- CFO metrikak: ha osszesitett penzugyi adatrol, KPI-rol, EBITDA-rol, bevetelrol, trendrol kerdeznek,
--   ELOSZOR probald a cfo_metrics tablabol lekerdezni (gyorsabb, elokalkulalt)
-- cfo_metrics.metric_key ertekek: invoice_total_count, invoice_processed_gross_amount, budget_variance,
--   overdue_invoice_amount, pnl_revenue, pnl_ebitda, pnl_net_income, error_rate_pct, stb.
""".strip()

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "question": "Hany szamla van a rendszerben?",
        "sql": "SELECT COUNT(*) AS szamla_db FROM invoices LIMIT 100;",
    },
    {
        "question": "Hany feldolgozott szamla van?",
        "sql": "SELECT COUNT(*) AS feldolgozott_db FROM invoices WHERE status IN ('approved','in_approval','awaiting_match','matched','posted','pending_review') LIMIT 100;",
    },
    {
        "question": "Mi a feldolgozott szamlak brutto osszege?",
        "sql": "SELECT SUM(gross_amount) AS osszes_brutto FROM invoices WHERE status IN ('approved','in_approval','awaiting_match','matched','posted','pending_review') LIMIT 100;",
    },
    {
        "question": "Melyik osztaly lepte tul a budget-ot?",
        "sql": "SELECT d.name, bl.period, SUM(bl.planned_amount) AS terv, COALESCE(SUM(ae.amount),0) AS teny, COALESCE(SUM(ae.amount),0) - SUM(bl.planned_amount) AS elteres FROM budget_lines bl JOIN departments d ON d.id = bl.department_id LEFT JOIN accounting_entries ae ON ae.department_id = bl.department_id AND ae.period = bl.period GROUP BY d.name, bl.period HAVING COALESCE(SUM(ae.amount),0) > SUM(bl.planned_amount) ORDER BY elteres DESC LIMIT 100;",
    },
    {
        "question": "Top 5 szallito osszeg szerint",
        "sql": "SELECT p.name, SUM(i.gross_amount) AS osszeg FROM invoices i JOIN partners p ON p.id = i.partner_id WHERE i.gross_amount IS NOT NULL GROUP BY p.name ORDER BY osszeg DESC LIMIT 5;",
    },
    {
        "question": "Mennyi a jovahagyasra varo szamlak osszes brutto osszege?",
        "sql": "SELECT SUM(gross_amount) AS jovahagyasra_varo_osszeg FROM invoices WHERE status = 'in_approval' LIMIT 100;",
    },
    {
        "question": "Hany partner van a rendszerben?",
        "sql": "SELECT COUNT(*) AS partner_db FROM partners LIMIT 100;",
    },
    {
        "question": "Melyik szallitotol erkezett a legtobb szamla?",
        "sql": "SELECT p.name, COUNT(i.id) AS szamla_db FROM invoices i JOIN partners p ON p.id = i.partner_id GROUP BY p.name ORDER BY szamla_db DESC LIMIT 5;",
    },
    {
        "question": "Lejart hatarideju szamlak listaja",
        "sql": "SELECT i.invoice_number, p.name AS partner, i.gross_amount, i.due_date, i.status FROM invoices i LEFT JOIN partners p ON p.id = i.partner_id WHERE i.due_date < CURRENT_DATE AND i.status NOT IN ('posted','rejected','error') ORDER BY i.due_date ASC LIMIT 100;",
    },
    {
        "question": "Havi szamla beerkedes statisztika",
        "sql": "SELECT TO_CHAR(created_at, 'YYYY-MM') AS honap, COUNT(*) AS szamla_db FROM invoices GROUP BY TO_CHAR(created_at, 'YYYY-MM') ORDER BY honap DESC LIMIT 100;",
    },
    {
        "question": "Duplikat szamlak listaja",
        "sql": "SELECT i.invoice_number, p.name AS partner, i.gross_amount, i.status FROM invoices i LEFT JOIN partners p ON p.id = i.partner_id WHERE i.is_duplicate = TRUE LIMIT 100;",
    },
    {
        "question": "Megrendelesek statusza osztaly szerint",
        "sql": "SELECT d.name AS osztaly, po.status, COUNT(*) AS db FROM purchase_orders po JOIN departments d ON d.id = po.department_id GROUP BY d.name, po.status ORDER BY d.name, po.status LIMIT 100;",
    },
    {
        "question": "Felhasznalok listaja osztaly nevvel",
        "sql": "SELECT u.full_name, u.email, u.role, d.name AS osztaly FROM users u LEFT JOIN departments d ON d.id = u.department_id WHERE u.is_active = TRUE ORDER BY u.full_name LIMIT 100;",
    },
    {
        "question": "Atlagos szamla osszeg partnerre vetitve",
        "sql": "SELECT p.name, AVG(i.gross_amount) AS atlag_osszeg, COUNT(i.id) AS szamla_db FROM invoices i JOIN partners p ON p.id = i.partner_id WHERE i.gross_amount IS NOT NULL GROUP BY p.name ORDER BY atlag_osszeg DESC LIMIT 100;",
    },
    {
        "question": "Mennyi a postazott szamlak osszege honap szerint?",
        "sql": "SELECT TO_CHAR(i.approved_at, 'YYYY-MM') AS honap, SUM(i.gross_amount) AS osszeg FROM invoices i WHERE i.status = 'posted' AND i.approved_at IS NOT NULL GROUP BY TO_CHAR(i.approved_at, 'YYYY-MM') ORDER BY honap DESC LIMIT 100;",
    },
    {
        "question": "Melyik osztaly kolti a legtobbet?",
        "sql": "SELECT d.name, SUM(ae.amount) AS osszes_koltes FROM accounting_entries ae JOIN departments d ON d.id = ae.department_id GROUP BY d.name ORDER BY osszes_koltes DESC LIMIT 100;",
    },
    {
        "question": "Jovahagyasi folyamat statisztika",
        "sql": "SELECT ia.step_name, ia.status, COUNT(*) AS db FROM invoice_approvals ia GROUP BY ia.step_name, ia.status ORDER BY ia.step_name, ia.status LIMIT 100;",
    },
    {
        "question": "Szamla statuszok megoszlasa",
        "sql": "SELECT status, COUNT(*) AS db FROM invoices GROUP BY status ORDER BY db DESC LIMIT 100;",
    },
    # === CFO Metrics few-shots ===
    {
        "question": "Mennyi volt a bevetel idén januarban?",
        "sql": "SELECT value AS bevetel FROM cfo_metrics WHERE metric_key = 'pnl_revenue' AND period = '2025-01' LIMIT 1;",
    },
    {
        "question": "Mi az EBITDA az aktualis honapban?",
        "sql": "SELECT value AS ebitda FROM cfo_metrics WHERE metric_key = 'pnl_ebitda' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "Mennyi lejart hatarideju szamla van?",
        "sql": "SELECT value AS lejart_db FROM cfo_metrics WHERE metric_key = 'overdue_invoice_count' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "Koltsegvetesi elteres az aktualis honapban?",
        "sql": "SELECT value AS elteres FROM cfo_metrics WHERE metric_key = 'budget_variance' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "Osszes CFO metrika az aktualis honapban",
        "sql": "SELECT metric_key, value FROM cfo_metrics WHERE period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') ORDER BY metric_key LIMIT 100;",
    },
    {
        "question": "Havi bevetel trend az utolso felev",
        "sql": "SELECT period, value AS bevetel FROM cfo_metrics WHERE metric_key = 'pnl_revenue' ORDER BY period DESC LIMIT 6;",
    },
    {
        "question": "Mennyi a netto eredmeny?",
        "sql": "SELECT value AS netto_eredmeny FROM cfo_metrics WHERE metric_key = 'pnl_net_income' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "Mekkora a hibaarany a szamlafeldolgozasban?",
        "sql": "SELECT value AS hiba_pct FROM cfo_metrics WHERE metric_key = 'error_rate_pct' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "Mennyi a tervezett koltsegvetes 2024-ben?",
        "sql": "SELECT SUM(value) AS tervezett_koltsegvetes FROM cfo_metrics WHERE metric_key = 'budget_planned_total' AND period LIKE '2024%' LIMIT 1;",
    },
    {
        "question": "Eves EBITDA 2024-ben?",
        "sql": "SELECT SUM(value) AS eves_ebitda FROM cfo_metrics WHERE metric_key = 'pnl_ebitda' AND period LIKE '2024%' LIMIT 1;",
    },
    {
        "question": "Havi bevetelek 2024-ben",
        "sql": "SELECT period, value AS bevetel FROM cfo_metrics WHERE metric_key = 'pnl_revenue' AND period LIKE '2024%' ORDER BY period LIMIT 12;",
    },
    {
        "question": "Budget elteres havonta 2024-ben",
        "sql": "SELECT period, value AS elteres FROM cfo_metrics WHERE metric_key = 'budget_variance' AND period LIKE '2024%' ORDER BY period LIMIT 12;",
    },
    # === Forecast few-shots ===
    {
        "question": "Cash flow elorejelezes a kovetkezo 30 napra",
        "sql": "SELECT metric_key, value FROM cfo_metrics WHERE metric_key IN ('forecast_cash_in_30d','forecast_cash_out_30d','forecast_net_cash_30d') AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 10;",
    },
    {
        "question": "Mennyi lesz a varhato netto cash flow 90 napon belul?",
        "sql": "SELECT value AS netto_cash_90d FROM cfo_metrics WHERE metric_key = 'forecast_net_cash_90d' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    # === YoY few-shots ===
    {
        "question": "Hogyan valtozott a bevetel az elozo evhez kepest?",
        "sql": "SELECT value AS bevetel_yoy_pct FROM cfo_metrics WHERE metric_key = 'revenue_yoy_change_pct' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
    {
        "question": "EBITDA valtozas tavaly ota",
        "sql": "SELECT value AS ebitda_yoy_pct FROM cfo_metrics WHERE metric_key = 'ebitda_yoy_change_pct' AND period = TO_CHAR(CURRENT_DATE, 'YYYY-MM') LIMIT 1;",
    },
]
