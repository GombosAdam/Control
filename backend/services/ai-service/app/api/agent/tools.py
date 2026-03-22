TOOL_DEFINITIONS = [
    {
        "name": "get_budget_summary",
        "description": "Budget státusz osztályonként: tervezett, elkötött (PO), tényleges költés, szabad keret, kihasználtság %. Opcionálisan egy osztályra szűrhető.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Osztály neve (pl. 'IT', 'Marketing'). Ha üres, minden osztályt mutat.",
                }
            },
        },
    },
    {
        "name": "get_invoice_stats",
        "description": "Számla statisztikák: darabszám státuszonként, összegek, lejártak, duplikált gyanúsak. Opcionálisan státuszra vagy partnerre szűrhető.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Számla státusz szűrő (pl. 'pending_review', 'posted', 'error')",
                },
                "partner": {
                    "type": "string",
                    "description": "Partner/szállító neve",
                },
            },
        },
    },
    {
        "name": "get_partner_detail",
        "description": "Egy partner/szállító részletes adatai: számlák listája, összegek, fizetési minta. Partner neve vagy ID-ja alapján.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_id": {
                    "type": "string",
                    "description": "Partner neve (pl. 'CloudHost') vagy UUID-ja",
                }
            },
            "required": ["name_or_id"],
        },
    },
    {
        "name": "get_anomalies",
        "description": "Aktív anomáliák és figyelmeztetések: budget túllépések, lejárt számlák, duplikátok, kiugró összegek.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "Szűrés súlyosságra: 'critical' vagy 'warning'",
                }
            },
        },
    },
    {
        "name": "get_cash_position",
        "description": "Pénzügyi helyzet: tervezett budget vs tényleges költés, EBITDA osztályonként, margin %. Opcionálisan osztályra és periódusra szűrhető.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Osztály neve",
                },
                "period": {
                    "type": "string",
                    "description": "Periódus YYYY-MM formátumban",
                },
            },
        },
    },
    {
        "name": "search_history",
        "description": "Korábbi hasonló kérdések keresése a rendszerben. Szemantikus keresés a korábbi kérdés-válasz párok között.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "A keresett téma vagy kérdés",
                }
            },
            "required": ["topic"],
        },
    },
    {
        "name": "execute_sql",
        "description": "SQL lekérdezés futtatása a pénzügyi adatbázison. Csak SELECT engedélyezett. Használd, ha a többi tool nem ad elég részletes adatot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A futtatandó SQL SELECT lekérdezés",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_forecast",
        "description": "Cash flow előrejelzés 30/60/90 napra: várható bevétel, kiadás és nettó pénzáramlás. Historikus átlag + nyitott PO-k + budget forecast alapján.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "simulate_scenario",
        "description": "What-if szimuláció: mi történne ha egy osztály budget-jét megváltoztatnánk. Kiszámolja az EBITDA, net income és margin változást. NEM ír adatbázisba.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Osztály neve (pl. 'IT', 'Marketing')",
                },
                "budget_change_pct": {
                    "type": "number",
                    "description": "Budget változás százalékban (pl. -20 = 20%-os csökkentés, +15 = 15%-os növelés)",
                },
                "pnl_category": {
                    "type": "string",
                    "description": "P&L kategória szűrő (opcionális): 'revenue', 'cogs', 'opex', 'depreciation', 'interest', 'tax'",
                },
            },
            "required": ["department", "budget_change_pct"],
        },
    },
    {
        "name": "get_yoy_comparison",
        "description": "Év/év (YoY) összehasonlítás: bevétel, kiadás, EBITDA és számlaszám változás az előző év azonos hónapjához képest.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Osztály neve (opcionális)",
                },
                "period": {
                    "type": "string",
                    "description": "Periódus YYYY-MM formátumban (alapértelmezett: aktuális hónap)",
                },
            },
        },
    },
    {
        "name": "get_approval_bottleneck",
        "description": "Jóváhagyási folyamat szűk keresztmetszet elemzés: átlagos idő lépésenként, lassú döntéshozók, függő jóváhagyások.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Periódus YYYY-MM formátumban (opcionális)",
                },
            },
        },
    },
    {
        "name": "get_supplier_risk",
        "description": "Szállítói kockázat elemzés: átlagos fizetési napok, függőségi kockázat (>20% részesedés), ártrendek. Opcionálisan egy szállítóra szűrhető.",
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier": {
                    "type": "string",
                    "description": "Szállító neve (opcionális — ha üres, összesített elemzés)",
                },
            },
        },
    },
    {
        "name": "get_aging_report",
        "description": "Korosítási jelentés: lejárt számlák korbontása (0-30, 31-60, 61-90, 90+ nap). Partner szűrő nélkül top 5 partnert is mutat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "partner": {
                    "type": "string",
                    "description": "Partner/szállító neve (opcionális — ha üres, összesített + top 5 partner)",
                },
            },
        },
    },
    {
        "name": "get_budget_trend",
        "description": "Budget felhasználási trend: havi tervezett vs tényleges, kihasználtság %, burn rate előrejelzés. Osztályra és időszakra szűrhető.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Osztály neve (opcionális)",
                },
                "months": {
                    "type": "integer",
                    "description": "Visszatekintés hónapokban (alapértelmezett: 6, maximum: 12)",
                },
            },
        },
    },
    {
        "name": "get_working_capital",
        "description": "Forgótőke mutatók: DSO (vevői fizetési napok), DPO (szállítói fizetési napok), CCC (pénzforgási ciklus). Megmutatja milyen gyorsan mozog a pénz.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]
