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
]
