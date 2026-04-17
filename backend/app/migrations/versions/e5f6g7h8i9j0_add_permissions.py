"""add permissions and role_permissions tables with seed data

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-04-16 15:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Permission seed: (resource, action, description)
PERMISSIONS = [
    # Dashboard & Chat — open to all
    ("dashboard", "read", "Irányítópult megtekintése"),
    ("chat", "read", "AI Chat használata"),

    # Invoices
    ("invoices", "read", "Számlák listázása és megtekintése"),
    ("invoices", "upload", "Számlák feltöltése"),
    ("invoices", "update", "Számlák szerkesztése"),
    ("invoices", "delete", "Számlák törlése"),
    ("invoices", "approve", "Számlák jóváhagyása/elutasítása"),
    ("invoices.extraction", "read", "Kinyerési sor megtekintése"),
    ("invoices.extraction", "process", "Kinyerés feldolgozása"),

    # Partners
    ("partners", "read", "Partnerek megtekintése"),
    ("partners", "create", "Partnerek létrehozása"),
    ("partners", "update", "Partnerek szerkesztése"),

    # Reconciliation
    ("reconciliation", "read", "Egyeztetés megtekintése"),

    # Accounting
    ("accounting", "read", "Könyvelés megtekintése"),
    ("accounting", "create", "Könyvelési tételek létrehozása"),
    ("accounting", "update", "Könyvelési tételek szerkesztése"),
    ("accounting.templates", "manage", "Könyvelési tükör kezelése"),

    # Budget
    ("budget", "read", "Budget keretek megtekintése"),
    ("budget", "create", "Budget sorok létrehozása"),
    ("budget", "update", "Budget sorok szerkesztése"),
    ("budget", "delete", "Budget sorok törlése"),
    ("budget.comments", "create", "Budget megjegyzések írása"),

    # Orders (PO)
    ("orders", "read", "Megrendelések megtekintése"),
    ("orders", "create", "Megrendelések létrehozása"),

    # Controlling & Reports
    ("controlling", "read", "Controlling nézetek megtekintése"),
    ("reports", "read", "Riportok megtekintése"),

    # Scenarios
    ("scenarios", "read", "Szcenáriók megtekintése"),
    ("scenarios", "create", "Szcenáriók létrehozása"),
    ("scenarios", "delete", "Szcenáriók törlése"),

    # Planning periods
    ("planning_periods", "read", "Tervezési időszakok megtekintése"),
    ("planning_periods", "manage", "Tervezési időszakok kezelése"),

    # Admin
    ("admin.users", "read", "Felhasználók listázása"),
    ("admin.users", "create", "Felhasználók létrehozása"),
    ("admin.users", "update", "Felhasználók szerkesztése"),
    ("admin.users", "delete", "Felhasználók törlése"),
    ("admin.settings", "read", "Beállítások megtekintése"),
    ("admin.settings", "update", "Beállítások módosítása"),
    ("admin.system", "read", "Rendszer állapot megtekintése"),
    ("admin.audit", "read", "Audit napló megtekintése"),
    ("admin.departments", "manage", "Osztályok kezelése"),
    ("admin.positions", "manage", "Pozíciók kezelése"),
    ("admin.po_approvals", "manage", "PO jóváhagyások admin nézete"),
    ("admin.gpu", "manage", "GPU kezelése"),
    ("admin.permissions", "manage", "Jogosultság mátrix kezelése"),

    # NAV
    ("nav.config", "read", "NAV konfiguráció megtekintése"),
    ("nav.config", "update", "NAV konfiguráció módosítása"),
    ("nav.config", "delete", "NAV konfiguráció törlése"),
    ("nav.sync", "read", "NAV szinkron napló megtekintése"),
    ("nav.sync", "trigger", "NAV szinkron indítása"),
    ("nav.transactions", "read", "NAV tranzakciók megtekintése"),
    ("nav.transactions", "update", "NAV tranzakciók frissítése"),
]

# Role-permission mappings: role -> list of (resource, action) tuples
ROLE_PERMISSIONS = {
    "admin": "*",  # admin gets everything
    "cfo": [
        ("dashboard", "read"), ("chat", "read"),
        ("invoices", "read"),
        ("reconciliation", "read"),
        ("accounting", "read"),
        ("budget", "read"), ("budget", "create"), ("budget", "update"), ("budget", "delete"),
        ("budget.comments", "create"),
        ("orders", "read"), ("orders", "create"),
        ("controlling", "read"), ("reports", "read"),
        ("scenarios", "read"), ("scenarios", "create"),
        ("planning_periods", "read"), ("planning_periods", "manage"),
    ],
    "department_head": [
        ("dashboard", "read"), ("chat", "read"),
        ("invoices", "read"),
        ("budget", "read"), ("budget", "create"), ("budget", "update"),
        ("budget.comments", "create"),
        ("orders", "read"), ("orders", "create"),
        ("controlling", "read"), ("reports", "read"),
    ],
    "accountant": [
        ("dashboard", "read"), ("chat", "read"),
        ("invoices", "read"), ("invoices", "upload"), ("invoices", "update"), ("invoices", "delete"),
        ("invoices", "approve"),
        ("invoices.extraction", "read"), ("invoices.extraction", "process"),
        ("partners", "read"), ("partners", "create"), ("partners", "update"),
        ("reconciliation", "read"),
        ("accounting", "read"), ("accounting", "create"), ("accounting", "update"),
        ("budget", "read"), ("budget.comments", "create"),
        ("orders", "read"), ("orders", "create"),
        ("nav.config", "read"), ("nav.config", "update"),
        ("nav.sync", "read"), ("nav.sync", "trigger"),
        ("nav.transactions", "read"), ("nav.transactions", "update"),
    ],
    "reviewer": [
        ("dashboard", "read"), ("chat", "read"),
        ("invoices", "read"), ("invoices", "approve"),
    ],
    "clerk": [
        ("dashboard", "read"), ("chat", "read"),
        ("invoices", "read"),
        ("orders", "read"), ("orders", "create"),
    ],
}


def upgrade() -> None:
    # Create tables
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('resource', sa.String(100), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )

    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('role', sa.Enum('admin', 'cfo', 'department_head', 'accountant', 'reviewer', 'clerk', name='userrole', create_type=False), nullable=False, index=True),
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('role', 'permission_id', name='uq_role_permission'),
    )

    # Seed permissions
    permissions_table = sa.table(
        'permissions',
        sa.column('id', sa.String),
        sa.column('resource', sa.String),
        sa.column('action', sa.String),
        sa.column('description', sa.String),
    )

    role_permissions_table = sa.table(
        'role_permissions',
        sa.column('id', sa.String),
        sa.column('role', sa.String),
        sa.column('permission_id', sa.String),
    )

    # Insert permissions and build id lookup
    perm_ids = {}
    for resource, action, description in PERMISSIONS:
        pid = str(uuid.uuid4())
        perm_ids[(resource, action)] = pid
        op.execute(
            permissions_table.insert().values(
                id=pid, resource=resource, action=action, description=description,
            )
        )

    # Insert role_permissions
    for role, perms in ROLE_PERMISSIONS.items():
        if perms == "*":
            # Admin gets all permissions
            targets = [(r, a) for r, a, _ in PERMISSIONS]
        else:
            targets = perms

        for resource, action in targets:
            pid = perm_ids.get((resource, action))
            if pid:
                op.execute(
                    role_permissions_table.insert().values(
                        id=str(uuid.uuid4()), role=role, permission_id=pid,
                    )
                )


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_table('permissions')
