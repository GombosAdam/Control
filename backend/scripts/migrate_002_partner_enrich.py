"""
Migration 002: Partner master enrichment — new columns + seed update.
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


NEW_COLUMNS = [
    ("payment_terms_days", "INTEGER NOT NULL DEFAULT 30"),
    ("payment_method", "VARCHAR(50) NOT NULL DEFAULT 'transfer'"),
    ("currency", "VARCHAR(3) NOT NULL DEFAULT 'HUF'"),
    ("country_code", "VARCHAR(2) NOT NULL DEFAULT 'HU'"),
    ("city", "VARCHAR(100)"),
    ("zip_code", "VARCHAR(10)"),
    ("contact_person", "VARCHAR(255)"),
    ("contact_phone", "VARCHAR(50)"),
    ("iban", "VARCHAR(34)"),
    ("swift_code", "VARCHAR(11)"),
    ("is_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("notes", "TEXT"),
]

# Realistic partner enrichment data keyed by tax_number
PARTNER_UPDATES = {
    "12345678-2-42": {
        "city": "Budapest",
        "zip_code": "1052",
        "contact_person": "Kovács Péter",
        "contact_phone": "+36 1 234 5678",
        "iban": "HU42 1177 3016 1111 1018 0000 0000",
        "swift_code": "OTPVHUHB",
        "payment_terms_days": 30,
        "is_verified": True,
    },
    "87654321-2-41": {
        "city": "Debrecen",
        "zip_code": "4024",
        "contact_person": "Szabó Anna",
        "contact_phone": "+36 52 111 222",
        "iban": "HU93 1160 0006 0000 0000 1234 5678",
        "swift_code": "GIBAHUHB",
        "payment_terms_days": 45,
        "is_verified": True,
    },
    "11111111-2-43": {
        "city": "Győr",
        "zip_code": "9021",
        "contact_person": "Tóth László",
        "contact_phone": "+36 96 333 444",
        "payment_terms_days": 14,
        "is_verified": True,
    },
    "22222222-2-44": {
        "city": "Szeged",
        "zip_code": "6720",
        "contact_person": "Kiss Éva",
        "contact_phone": "+36 62 555 666",
        "payment_terms_days": 30,
        "is_verified": True,
    },
    "33333333-2-13": {
        "city": "Pécs",
        "zip_code": "7621",
        "contact_person": "Horváth Gábor",
        "contact_phone": "+36 72 777 888",
        "payment_terms_days": 60,
        "is_verified": True,
    },
    "44444444-2-02": {
        "city": "Miskolc",
        "zip_code": "3525",
        "contact_person": "Varga Katalin",
        "contact_phone": "+36 46 999 000",
        "iban": "HU12 1040 0000 0000 0000 0000 0000",
        "swift_code": "OKHBHUHB",
        "payment_terms_days": 30,
        "is_verified": True,
    },
    "55555555-2-07": {
        "city": "Székesfehérvár",
        "zip_code": "8000",
        "contact_person": "Balogh Zoltán",
        "contact_phone": "+36 22 111 333",
        "payment_terms_days": 30,
        "is_verified": False,
    },
    "66666666-2-18": {
        "city": "Nyíregyháza",
        "zip_code": "4400",
        "contact_person": "Fekete Mária",
        "contact_phone": "+36 42 222 444",
        "payment_terms_days": 15,
        "is_verified": True,
    },
    "77777777-2-09": {
        "city": "Kecskemét",
        "zip_code": "6000",
        "contact_person": "Takács József",
        "contact_phone": "+36 76 333 555",
        "payment_terms_days": 30,
        "is_verified": True,
    },
    "88888888-2-20": {
        "city": "Szombathely",
        "zip_code": "9700",
        "contact_person": "Simon Erzsébet",
        "contact_phone": "+36 94 444 666",
        "payment_terms_days": 45,
        "is_verified": False,
    },
    "99999999-2-11": {
        "city": "Eger",
        "zip_code": "3300",
        "contact_person": "Németh Attila",
        "contact_phone": "+36 36 555 777",
        "payment_terms_days": 30,
        "is_verified": True,
    },
    "10101010-2-05": {
        "city": "Veszprém",
        "zip_code": "8200",
        "contact_person": "Molnár Zsuzsa",
        "contact_phone": "+36 88 666 888",
        "payment_terms_days": 30,
        "is_verified": True,
    },
}


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Add new columns
        for col_name, col_def in NEW_COLUMNS:
            cur.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE partners ADD COLUMN {col_name} {col_def};
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)

        conn.commit()

        # 2. Update partners with enrichment data
        for tax_number, data in PARTNER_UPDATES.items():
            set_clauses = []
            values = []
            for key, value in data.items():
                set_clauses.append(f"{key} = %s")
                values.append(value)
            values.append(tax_number)

            if set_clauses:
                cur.execute(
                    f"UPDATE partners SET {', '.join(set_clauses)} WHERE tax_number = %s",
                    values,
                )

        conn.commit()
        print("Migration 002 complete: Partner enrichment columns added and seed data updated.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
