"""
Migration 008: Workflow engine tables (6 tables).
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Create enums
        for enum_name, values in [
            ("steptype", ("approval", "notification", "auto_action")),
            ("routingstrategy", ("fixed_role", "position_hierarchy", "department_manager")),
            ("workflowstatus", ("active", "completed", "rejected", "cancelled", "error")),
            ("taskstatus", ("waiting", "pending", "approved", "rejected", "skipped", "escalated", "cancelled", "timed_out")),
            ("ruletype", ("skip_step", "auto_approve", "route_override")),
        ]:
            vals = ", ".join(f"'{v}'" for v in values)
            cur.execute(f"""
                DO $$ BEGIN
                    CREATE TYPE {enum_name} AS ENUM ({vals});
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
            """)

        # 2. workflow_definitions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                id              VARCHAR(36) PRIMARY KEY,
                code            VARCHAR(50) NOT NULL UNIQUE,
                name            VARCHAR(255) NOT NULL,
                entity_type     VARCHAR(50) NOT NULL,
                version         INTEGER NOT NULL DEFAULT 1,
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                trigger_event   VARCHAR(100) NOT NULL,
                config          JSONB,
                created_by      VARCHAR(36) REFERENCES users(id),
                created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_definitions_entity_type
            ON workflow_definitions(entity_type);
        """)

        # 3. workflow_step_definitions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_step_definitions (
                id                VARCHAR(36) PRIMARY KEY,
                workflow_id       VARCHAR(36) NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                step_order        INTEGER NOT NULL,
                step_code         VARCHAR(50) NOT NULL,
                step_name         VARCHAR(255) NOT NULL,
                step_type         steptype NOT NULL,
                routing_strategy  routingstrategy NOT NULL,
                assigned_role     VARCHAR(50),
                is_parallel       BOOLEAN NOT NULL DEFAULT FALSE,
                parallel_group    VARCHAR(50),
                skip_rules        JSONB,
                timeout_hours     INTEGER,
                escalation_role   VARCHAR(50),
                config            JSONB,
                created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(workflow_id, step_order),
                UNIQUE(workflow_id, step_code)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_step_definitions_workflow_id
            ON workflow_step_definitions(workflow_id);
        """)

        # 4. workflow_instances
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_instances (
                id                      VARCHAR(36) PRIMARY KEY,
                workflow_definition_id  VARCHAR(36) NOT NULL REFERENCES workflow_definitions(id),
                entity_type             VARCHAR(50) NOT NULL,
                entity_id               VARCHAR(36) NOT NULL,
                status                  workflowstatus NOT NULL DEFAULT 'active',
                current_step_order      INTEGER NOT NULL DEFAULT 1,
                context                 JSONB,
                initiated_by            VARCHAR(36) REFERENCES users(id),
                completed_at            TIMESTAMP,
                created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_instances_entity
            ON workflow_instances(entity_type, entity_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_instances_definition
            ON workflow_instances(workflow_definition_id);
        """)

        # 5. workflow_tasks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_tasks (
                id                  VARCHAR(36) PRIMARY KEY,
                instance_id         VARCHAR(36) NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
                step_definition_id  VARCHAR(36) NOT NULL REFERENCES workflow_step_definitions(id),
                step_order          INTEGER NOT NULL,
                step_name           VARCHAR(255) NOT NULL,
                status              taskstatus NOT NULL DEFAULT 'waiting',
                assigned_role       VARCHAR(50),
                assigned_to         VARCHAR(36) REFERENCES users(id),
                delegated_to        VARCHAR(36) REFERENCES users(id),
                parallel_group      VARCHAR(50),
                decided_by          VARCHAR(36) REFERENCES users(id),
                decided_at          TIMESTAMP,
                comment             TEXT,
                due_at              TIMESTAMP,
                escalated_at        TIMESTAMP,
                created_at          TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_tasks_instance_id
            ON workflow_tasks(instance_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_tasks_status_due
            ON workflow_tasks(status, due_at);
        """)

        # 6. workflow_rules
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_rules (
                id            VARCHAR(36) PRIMARY KEY,
                workflow_id   VARCHAR(36) NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                step_code     VARCHAR(50),
                rule_type     ruletype NOT NULL,
                name          VARCHAR(255) NOT NULL,
                priority      INTEGER NOT NULL DEFAULT 0,
                condition     JSONB NOT NULL,
                action        JSONB NOT NULL,
                is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_workflow_rules_workflow_id
            ON workflow_rules(workflow_id);
        """)

        # 7. delegations
        cur.execute("""
            CREATE TABLE IF NOT EXISTS delegations (
                id              VARCHAR(36) PRIMARY KEY,
                delegator_id    VARCHAR(36) NOT NULL REFERENCES users(id),
                delegate_id     VARCHAR(36) NOT NULL REFERENCES users(id),
                workflow_code   VARCHAR(50),
                valid_from      TIMESTAMP NOT NULL,
                valid_until     TIMESTAMP NOT NULL,
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_delegations_active
            ON delegations(delegator_id, is_active, valid_from, valid_until);
        """)

        conn.commit()
        print("Migration 008 OK — 6 workflow tables created")

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
