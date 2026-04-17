"""
Migration 003: Department hierarchy — Igazgatóság parent, manager fixes, budget master seed.
Idempotent — safe to re-run.
"""
import uuid
import psycopg2
from common.config import settings


DEPT_BUDGET_MASTER = {
    "FIN": [
        ("4100", "Termék értékesítés"), ("4200", "Szolgáltatás bevétel"), ("4300", "Egyéb bevétel"),
        ("5100", "Anyagköltség"), ("5110", "Alapanyag költség"), ("5120", "Alvállalkozói díj"), ("5130", "Közvetlen bérköltség"),
        ("6100", "Irodai költség"), ("6200", "Marketing költség"), ("6300", "IT költség"),
        ("6400", "Utazási költség"), ("6500", "Képzési költség"), ("6600", "Egyéb működési"),
        ("7100", "Tárgyi eszköz ÉCS"), ("7200", "Immat. javak ÉCS"),
        ("8100", "Kamatráfordítás"), ("8200", "Árfolyamveszteség"),
        ("9100", "Társasági adó"), ("9200", "Iparűzési adó"),
    ],
    "IT": [
        ("5100", "Anyagköltség"), ("6100", "Irodai költség"), ("6300", "IT költség"),
        ("7100", "Tárgyi eszköz ÉCS"), ("7200", "Immat. javak ÉCS"),
    ],
    "HR": [
        ("5130", "Közvetlen bérköltség"), ("6100", "Irodai költség"), ("6500", "Képzési költség"),
    ],
    "MKT": [
        ("6100", "Irodai költség"), ("6200", "Marketing költség"), ("6400", "Utazási költség"),
    ],
    "SALES": [
        ("4100", "Termék értékesítés"), ("4200", "Szolgáltatás bevétel"),
        ("6100", "Irodai költség"), ("6200", "Marketing költség"), ("6400", "Utazási költség"),
    ],
    "OPS": [
        ("5100", "Anyagköltség"), ("5110", "Alapanyag költség"), ("5120", "Alvállalkozói díj"),
        ("6100", "Irodai költség"), ("6400", "Utazási költség"), ("7100", "Tárgyi eszköz ÉCS"),
    ],
    "LOG": [
        ("5100", "Anyagköltség"), ("5120", "Alvállalkozói díj"),
        ("6100", "Irodai költség"), ("6400", "Utazási költség"), ("7100", "Tárgyi eszköz ÉCS"),
    ],
}


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Create Igazgatóság (MGMT) department if not exists
        cur.execute("SELECT id FROM departments WHERE code = 'MGMT'")
        mgmt_row = cur.fetchone()
        if not mgmt_row:
            mgmt_id = str(uuid.uuid4())
            # Use admin as manager
            cur.execute("SELECT id FROM users WHERE email = 'admin@invoice.local'")
            admin_row = cur.fetchone()
            admin_id = admin_row[0] if admin_row else None
            cur.execute("""
                INSERT INTO departments (id, name, code, parent_id, manager_id, created_at, updated_at)
                VALUES (%s, 'Igazgatóság', 'MGMT', NULL, %s, NOW(), NOW())
            """, (mgmt_id, admin_id))
            print(f"  Created Igazgatóság (MGMT) department: {mgmt_id}")
        else:
            mgmt_id = mgmt_row[0]
            print(f"  Igazgatóság (MGMT) already exists: {mgmt_id}")

        # 2. Set all other departments' parent_id to MGMT
        cur.execute("""
            UPDATE departments SET parent_id = %s
            WHERE code != 'MGMT' AND (parent_id IS NULL OR parent_id != %s)
        """, (mgmt_id, mgmt_id))
        updated = cur.rowcount
        print(f"  Updated {updated} departments to have MGMT as parent")

        # 3. Fix manager assignments
        # FIN → Nagy Mária (CFO)
        cur.execute("SELECT id FROM users WHERE full_name LIKE '%%Nagy Mária%%' OR full_name LIKE '%%Nagy Maria%%'")
        nagy_maria = cur.fetchone()
        if nagy_maria:
            cur.execute("UPDATE departments SET manager_id = %s WHERE code = 'FIN'", (nagy_maria[0],))
            print(f"  FIN manager → Nagy Mária ({nagy_maria[0]})")
        else:
            print("  Warning: Nagy Mária user not found, FIN manager unchanged")

        conn.commit()

        # 4. Seed department budget master entries
        for dept_code, accounts in DEPT_BUDGET_MASTER.items():
            cur.execute("SELECT id FROM departments WHERE code = %s", (dept_code,))
            dept_row = cur.fetchone()
            if not dept_row:
                print(f"  Warning: Department {dept_code} not found, skipping budget master")
                continue
            dept_id = dept_row[0]

            for account_code, account_name in accounts:
                cur.execute("""
                    INSERT INTO department_budget_master (id, department_id, account_code, account_name, is_active, created_at)
                    SELECT %s, %s, %s, %s, TRUE, NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM department_budget_master
                        WHERE department_id = %s AND account_code = %s
                    )
                """, (str(uuid.uuid4()), dept_id, account_code, account_name, dept_id, account_code))

        conn.commit()
        print("Migration 003 complete: Department hierarchy, manager fixes, and budget master seeded.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
