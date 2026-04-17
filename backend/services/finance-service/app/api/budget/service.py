import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.budget_line import BudgetLine, BudgetStatus, PlanType
from common.models.budget_line_comment import BudgetLineComment
from common.models.purchase_order import PurchaseOrder, POStatus
from common.models.accounting_entry import AccountingEntry
from common.models.audit import AuditLog
from common.models.user import User
from common.models.account_master import AccountMaster
from common.exceptions import NotFoundError, ValidationError


class BudgetService:
    @staticmethod
    async def _write_audit(db: AsyncSession, user_id: str, action: str, line: BudgetLine, details: dict | None = None):
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type="budget_line",
            entity_id=line.id,
            details=details or {},
        )
        db.add(log)

    @staticmethod
    async def list_lines(db: AsyncSession, department_id: str | None, period: str | None,
                         status: str | None, plan_type: str | None = None,
                         scenario_id: str | None = None, page: int = 1, limit: int = 50) -> dict:
        query = select(BudgetLine)
        count_query = select(func.count(BudgetLine.id))

        if department_id:
            query = query.where(BudgetLine.department_id == department_id)
            count_query = count_query.where(BudgetLine.department_id == department_id)
        if period:
            query = query.where(BudgetLine.period == period)
            count_query = count_query.where(BudgetLine.period == period)
        if status:
            query = query.where(BudgetLine.status == BudgetStatus(status))
            count_query = count_query.where(BudgetLine.status == BudgetStatus(status))
        if plan_type:
            query = query.where(BudgetLine.plan_type == plan_type)
            count_query = count_query.where(BudgetLine.plan_type == plan_type)
        if scenario_id:
            query = query.where(BudgetLine.scenario_id == scenario_id)
            count_query = count_query.where(BudgetLine.scenario_id == scenario_id)

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(BudgetLine.period, BudgetLine.account_code)
            .offset((page - 1) * limit).limit(limit)
        )
        lines = result.scalars().all()

        items = []
        for line in lines:
            item = BudgetService._to_dict(line)
            avail = await BudgetService._calc_availability(db, line)
            item.update(avail)
            items.append(item)

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def create_line(db: AsyncSession, data: dict, user_id: str) -> dict:
        # Validate account_code against account_master
        account_code = data.get("account_code")
        if account_code:
            account = await db.get(AccountMaster, account_code)
            if account:
                # Auto-fill account_name and pnl_category from master
                if not data.get("account_name") or data["account_name"] == account_code:
                    data["account_name"] = account.name
                if account.pnl_category and (not data.get("pnl_category") or data["pnl_category"] == "opex"):
                    data["pnl_category"] = account.pnl_category

        line = BudgetLine(**data, created_by=user_id)
        db.add(line)
        await db.flush()
        await BudgetService._write_audit(db, user_id, "budget_line.create", line, {
            "planned_amount": data.get("planned_amount"),
            "pnl_category": data.get("pnl_category"),
            "account_code": data.get("account_code"),
        })
        await db.commit()
        await db.refresh(line)
        return BudgetService._to_dict(line)

    @staticmethod
    async def update_line(db: AsyncSession, line_id: str, data: dict, user_id: str) -> dict:
        line = await db.get(BudgetLine, line_id)
        if not line:
            raise NotFoundError("Budget line not found")
        if line.status != BudgetStatus.draft:
            raise ValidationError("Only draft budget lines can be edited")
        old_values = {k: getattr(line, k) for k in data if data[k] is not None}
        for key, value in data.items():
            if value is not None:
                setattr(line, key, value)
        new_values = {k: v for k, v in data.items() if v is not None}
        await BudgetService._write_audit(db, user_id, "budget_line.update", line, {
            "old": old_values, "new": new_values,
        })
        await db.commit()
        await db.refresh(line)
        return BudgetService._to_dict(line)

    @staticmethod
    async def approve(db: AsyncSession, line_id: str, user_id: str) -> dict:
        line = await db.get(BudgetLine, line_id)
        if not line:
            raise NotFoundError("Budget line not found")
        if line.status != BudgetStatus.draft:
            raise ValidationError("Only draft lines can be approved")
        line.status = BudgetStatus.approved
        line.approved_by = user_id
        await BudgetService._write_audit(db, user_id, "budget_line.approve", line, {
            "old_status": "draft",
        })
        await db.commit()
        await db.refresh(line)

        # Publish event
        try:
            from common.events import event_bus
            import asyncio
            asyncio.create_task(event_bus.publish("budget.approved", {"budget_line_id": line.id}))
        except Exception:
            pass

        return BudgetService._to_dict(line)

    @staticmethod
    async def lock(db: AsyncSession, line_id: str, user_id: str) -> dict:
        line = await db.get(BudgetLine, line_id)
        if not line:
            raise NotFoundError("Budget line not found")
        if line.status != BudgetStatus.approved:
            raise ValidationError("Only approved lines can be locked")
        line.status = BudgetStatus.locked
        await BudgetService._write_audit(db, user_id, "budget_line.lock", line, {
            "old_status": "approved",
        })
        await db.commit()
        await db.refresh(line)

        # Publish event
        try:
            from common.events import event_bus
            import asyncio
            asyncio.create_task(event_bus.publish("budget.locked", {"budget_line_id": line.id}))
        except Exception:
            pass

        return BudgetService._to_dict(line)

    @staticmethod
    async def bulk_approve(db: AsyncSession, line_ids: list[str], user_id: str) -> dict:
        approved = []
        errors = []
        for lid in line_ids:
            line = await db.get(BudgetLine, lid)
            if not line:
                errors.append({"id": lid, "reason": "Not found"})
                continue
            if line.status != BudgetStatus.draft:
                errors.append({"id": lid, "reason": f"Status is {line.status.value}, expected draft"})
                continue
            if line.planned_amount <= 0:
                errors.append({"id": lid, "reason": "Planned amount must be > 0"})
                continue
            line.status = BudgetStatus.approved
            line.approved_by = user_id
            await BudgetService._write_audit(db, user_id, "budget_line.approve", line, {
                "old_status": "draft", "bulk": True,
            })
            approved.append(lid)
        await db.commit()
        return {"approved": approved, "errors": errors}

    @staticmethod
    async def bulk_lock(db: AsyncSession, line_ids: list[str], user_id: str) -> dict:
        locked = []
        errors = []
        for lid in line_ids:
            line = await db.get(BudgetLine, lid)
            if not line:
                errors.append({"id": lid, "reason": "Not found"})
                continue
            if line.status != BudgetStatus.approved:
                errors.append({"id": lid, "reason": f"Status is {line.status.value}, expected approved"})
                continue
            line.status = BudgetStatus.locked
            await BudgetService._write_audit(db, user_id, "budget_line.lock", line, {
                "old_status": "approved", "bulk": True,
            })
            locked.append(lid)
        await db.commit()
        return {"locked": locked, "errors": errors}

    @staticmethod
    async def copy_period(db: AsyncSession, source_period: str, target_period: str,
                          department_id: str | None, user_id: str) -> dict:
        query = select(BudgetLine).where(BudgetLine.period == source_period)
        if department_id:
            query = query.where(BudgetLine.department_id == department_id)
        result = await db.execute(query)
        source_lines = result.scalars().all()

        created = 0
        for sl in source_lines:
            # Check if same line already exists in target period
            existing = await db.scalar(
                select(func.count(BudgetLine.id)).where(
                    BudgetLine.department_id == sl.department_id,
                    BudgetLine.account_code == sl.account_code,
                    BudgetLine.period == target_period,
                )
            )
            if existing and existing > 0:
                continue
            new_line = BudgetLine(
                department_id=sl.department_id,
                account_code=sl.account_code,
                account_name=sl.account_name,
                period=target_period,
                planned_amount=sl.planned_amount,
                currency=sl.currency,
                pnl_category=sl.pnl_category,
                sort_order=sl.sort_order,
                plan_type=sl.plan_type,
                scenario_id=sl.scenario_id,
                created_by=user_id,
            )
            db.add(new_line)
            await db.flush()
            await BudgetService._write_audit(db, user_id, "budget_line.copy", new_line, {
                "source_period": source_period,
                "source_id": sl.id,
            })
            created += 1
        await db.commit()
        return {"created": created, "source_period": source_period, "target_period": target_period}

    @staticmethod
    async def bulk_adjust(db: AsyncSession, line_ids: list[str], percentage: float, user_id: str) -> dict:
        adjusted = []
        errors = []
        for lid in line_ids:
            line = await db.get(BudgetLine, lid)
            if not line:
                errors.append({"id": lid, "reason": "Not found"})
                continue
            if line.status != BudgetStatus.draft:
                errors.append({"id": lid, "reason": f"Status is {line.status.value}, only draft lines can be adjusted"})
                continue
            old_amount = float(line.planned_amount)
            line.planned_amount = round(float(line.planned_amount) * (1 + percentage / 100), 2)
            await BudgetService._write_audit(db, user_id, "budget_line.adjust", line, {
                "old_amount": old_amount,
                "new_amount": float(line.planned_amount),
                "percentage": percentage,
            })
            adjusted.append(lid)
        await db.commit()
        return {"adjusted": adjusted, "errors": errors}

    @staticmethod
    async def validate_approve(db: AsyncSession, line_ids: list[str]) -> dict:
        valid = []
        invalid = []
        warnings = []
        for lid in line_ids:
            line = await db.get(BudgetLine, lid)
            if not line:
                invalid.append({"id": lid, "reasons": ["Not found"]})
                continue
            reasons = []
            warns = []
            if line.status != BudgetStatus.draft:
                reasons.append(f"Status is {line.status.value}, expected draft")
            if line.planned_amount <= 0:
                reasons.append("Planned amount must be > 0")
            if not line.account_code or not line.account_code.strip():
                reasons.append("Account code is empty")
            if not line.account_name or not line.account_name.strip():
                reasons.append("Account name is empty")
            # Check if actual data exists
            from common.models.accounting_entry import EntryType as ET
            actual = await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.department_id == line.department_id,
                    AccountingEntry.account_code == line.account_code,
                    AccountingEntry.period == line.period,
                    AccountingEntry.entry_type == ET.debit,
                )
            ) or 0
            if float(actual) == 0:
                warns.append("No actual data yet for this line")
            if reasons:
                invalid.append({"id": lid, "reasons": reasons})
            else:
                valid.append(lid)
            if warns:
                warnings.append({"id": lid, "warnings": warns})
        return {"valid": valid, "invalid": invalid, "warnings": warnings}

    @staticmethod
    async def get_line_audit(db: AsyncSession, line_id: str, page: int, limit: int) -> dict:
        base_query = select(AuditLog).where(
            AuditLog.entity_type == "budget_line",
            AuditLog.entity_id == line_id,
        )
        count = await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entity_type == "budget_line",
                AuditLog.entity_id == line_id,
            )
        ) or 0

        result = await db.execute(
            base_query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        logs = result.scalars().all()

        items = []
        for log in logs:
            user_name = None
            if log.user_id:
                user = await db.get(User, log.user_id)
                if user:
                    user_name = user.name if hasattr(user, 'name') else user.email
            items.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_name": user_name,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            })

        return {
            "items": items,
            "total": count,
            "page": page,
            "limit": limit,
            "pages": math.ceil(count / limit) if count > 0 else 1,
        }

    @staticmethod
    async def get_periods(db: AsyncSession) -> list[str]:
        result = await db.execute(
            select(BudgetLine.period).distinct().order_by(BudgetLine.period)
        )
        return [r[0] for r in result.all()]

    @staticmethod
    async def get_availability(db: AsyncSession, dept_id: str) -> list[dict]:
        # Check if department has budget master entries
        from common.models.department_budget_master import DepartmentBudgetMaster
        master_result = await db.execute(
            select(DepartmentBudgetMaster.account_code).where(
                DepartmentBudgetMaster.department_id == dept_id,
                DepartmentBudgetMaster.is_active == True,
            )
        )
        allowed_codes = [r[0] for r in master_result.all()]

        query = select(BudgetLine).where(
            BudgetLine.department_id == dept_id,
            BudgetLine.status.in_([BudgetStatus.approved, BudgetStatus.locked]),
        )
        if allowed_codes:
            query = query.where(BudgetLine.account_code.in_(allowed_codes))

        result = await db.execute(query.order_by(BudgetLine.period, BudgetLine.account_code))
        lines = result.scalars().all()

        items = []
        for line in lines:
            item = BudgetService._to_dict(line)
            avail = await BudgetService._calc_availability(db, line)
            item.update(avail)
            items.append(item)
        return items

    @staticmethod
    async def _calc_availability(db: AsyncSession, line: BudgetLine) -> dict:
        committed = await db.scalar(
            select(func.coalesce(func.sum(PurchaseOrder.amount), 0)).where(
                PurchaseOrder.budget_line_id == line.id,
                PurchaseOrder.status.in_([POStatus.draft, POStatus.approved, POStatus.received, POStatus.closed]),
            )
        ) or 0

        from common.models.accounting_entry import EntryType
        actual = await db.scalar(
            select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                AccountingEntry.department_id == line.department_id,
                AccountingEntry.account_code == line.account_code,
                AccountingEntry.period == line.period,
                AccountingEntry.entry_type == EntryType.debit,
            )
        ) or 0

        planned = float(line.planned_amount)
        committed_f = float(committed)
        actual_f = float(actual)
        return {
            "committed": committed_f,
            "actual": actual_f,
            "available": planned - committed_f - actual_f,
        }

    @staticmethod
    def _to_dict(line: BudgetLine) -> dict:
        return {
            "id": line.id,
            "department_id": line.department_id,
            "department_name": line.department.name if line.department else None,
            "account_code": line.account_code,
            "account_name": line.account_name,
            "period": line.period,
            "planned_amount": float(line.planned_amount),
            "currency": line.currency,
            "status": line.status.value,
            "pnl_category": line.pnl_category,
            "sort_order": line.sort_order,
            "plan_type": line.plan_type.value if hasattr(line.plan_type, 'value') else line.plan_type,
            "scenario_id": line.scenario_id,
            "scenario_name": line.scenario.name if line.scenario else None,
            "planning_period_id": line.planning_period_id,
            "created_by": line.created_by,
            "creator_name": line.creator.name if line.creator and hasattr(line.creator, 'name') else (line.creator.email if line.creator else None),
            "approved_by": line.approved_by,
            "approver_name": line.approver.name if line.approver and hasattr(line.approver, 'name') else (line.approver.email if line.approver else None),
            "created_at": line.created_at.isoformat(),
            "updated_at": line.updated_at.isoformat(),
        }

    @staticmethod
    async def get_line_budget_status(db: AsyncSession, line_id: str) -> dict:
        """Get budget line with PO breakdown — for PO creation & approval context."""
        line = await db.get(BudgetLine, line_id)
        if not line:
            raise NotFoundError("Budget line not found")

        avail = await BudgetService._calc_availability(db, line)

        # Get POs on this budget line
        result = await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.budget_line_id == line_id,
                PurchaseOrder.status.in_([POStatus.draft, POStatus.approved, POStatus.received, POStatus.closed]),
            ).order_by(PurchaseOrder.created_at.desc())
        )
        pos = result.scalars().all()

        po_list = []
        for po in pos:
            creator_name = po.creator.full_name if po.creator else None
            po_list.append({
                "id": po.id,
                "po_number": po.po_number,
                "supplier_name": po.supplier_name,
                "amount": po.amount,
                "currency": po.currency,
                "status": po.status.value,
                "created_by_name": creator_name,
                "created_at": po.created_at.isoformat(),
            })

        return {
            "budget_line": {
                "id": line.id,
                "account_code": line.account_code,
                "account_name": line.account_name,
                "period": line.period,
                "planned_amount": float(line.planned_amount),
                "currency": line.currency,
            },
            "committed": avail["committed"],
            "actual": avail["actual"],
            "available": avail["available"],
            "purchase_orders": po_list,
        }

    @staticmethod
    async def create_year_plan(db: AsyncSession, year: int, source_year: int | None,
                               adjustment_pct: float, department_id: str | None,
                               plan_type: str, scenario_id: str | None,
                               user_id: str, start_month: int = 1, end_month: int = 12,
                               planning_period_id: str | None = None) -> dict:
        created = 0
        if source_year:
            # Copy from source year
            query = select(BudgetLine).where(
                BudgetLine.period.like(f"{source_year}-%")
            )
            if department_id:
                query = query.where(BudgetLine.department_id == department_id)
            if scenario_id:
                query = query.where(BudgetLine.scenario_id == scenario_id)
            result = await db.execute(query)
            source_lines = result.scalars().all()

            for sl in source_lines:
                src_month_int = int(sl.period.split("-")[1])
                if src_month_int < start_month or src_month_int > end_month:
                    continue
                src_month = sl.period.split("-")[1]
                new_period = f"{year}-{src_month}"
                # Duplicate check
                existing = await db.scalar(
                    select(func.count(BudgetLine.id)).where(
                        BudgetLine.department_id == sl.department_id,
                        BudgetLine.account_code == sl.account_code,
                        BudgetLine.period == new_period,
                        BudgetLine.plan_type == plan_type,
                        BudgetLine.scenario_id == (scenario_id or sl.scenario_id),
                    )
                )
                if existing and existing > 0:
                    continue
                new_line = BudgetLine(
                    department_id=sl.department_id,
                    account_code=sl.account_code,
                    account_name=sl.account_name,
                    period=new_period,
                    planned_amount=round(sl.planned_amount * (1 + adjustment_pct / 100), 2),
                    currency=sl.currency,
                    pnl_category=sl.pnl_category,
                    sort_order=sl.sort_order,
                    plan_type=plan_type,
                    scenario_id=scenario_id or sl.scenario_id,
                    planning_period_id=planning_period_id,
                    created_by=user_id,
                )
                db.add(new_line)
                await db.flush()
                await BudgetService._write_audit(db, user_id, "budget_line.create_year_plan", new_line, {
                    "source_year": source_year,
                    "source_id": sl.id,
                    "adjustment_pct": adjustment_pct,
                })
                created += 1
        else:
            # Create placeholder lines for months x 6 categories
            categories = [
                ("revenue", "REV-001", "Bevétel", 0),
                ("cogs", "COGS-001", "Közvetlen költség", 10),
                ("opex", "OPEX-001", "Működési költség", 20),
                ("depreciation", "DEP-001", "Értékcsökkenés", 30),
                ("interest", "INT-001", "Kamatköltség", 40),
                ("tax", "TAX-001", "Adó", 50),
            ]
            for m in range(start_month, end_month + 1):
                period = f"{year}-{m:02d}"
                for cat, code, name, sort in categories:
                    dup_filter = [
                        BudgetLine.account_code == code,
                        BudgetLine.period == period,
                        BudgetLine.plan_type == plan_type,
                    ]
                    if scenario_id:
                        dup_filter.append(BudgetLine.scenario_id == scenario_id)
                    if department_id:
                        dup_filter.append(BudgetLine.department_id == department_id)
                    existing = await db.scalar(
                        select(func.count(BudgetLine.id)).where(*dup_filter)
                    )
                    if existing and existing > 0:
                        continue
                    # Need a department -- use first available or the filtered one
                    dept = department_id
                    if not dept:
                        from common.models.department import Department
                        dept_result = await db.scalar(select(Department.id).limit(1))
                        dept = dept_result or "unknown"
                    new_line = BudgetLine(
                        department_id=dept,
                        account_code=code,
                        account_name=name,
                        period=period,
                        planned_amount=0,
                        pnl_category=cat,
                        sort_order=sort,
                        plan_type=plan_type,
                        scenario_id=scenario_id,
                        planning_period_id=planning_period_id,
                        created_by=user_id,
                    )
                    db.add(new_line)
                    await db.flush()
                    await BudgetService._write_audit(db, user_id, "budget_line.create_year_plan", new_line, {
                        "year": year,
                        "empty_plan": True,
                    })
                    created += 1
        await db.commit()
        return {"created": created, "year": year}

    @staticmethod
    async def create_forecast_from_budget(db: AsyncSession, source_period: str | None,
                                          department_id: str | None, adjustment_pct: float,
                                          scenario_id: str | None, user_id: str) -> dict:
        query = select(BudgetLine).where(BudgetLine.plan_type == PlanType.budget)
        if source_period:
            query = query.where(BudgetLine.period == source_period)
        if department_id:
            query = query.where(BudgetLine.department_id == department_id)
        if scenario_id:
            query = query.where(BudgetLine.scenario_id == scenario_id)

        result = await db.execute(query)
        source_lines = result.scalars().all()

        created = 0
        for sl in source_lines:
            existing = await db.scalar(
                select(func.count(BudgetLine.id)).where(
                    BudgetLine.department_id == sl.department_id,
                    BudgetLine.account_code == sl.account_code,
                    BudgetLine.period == sl.period,
                    BudgetLine.plan_type == PlanType.forecast,
                    BudgetLine.scenario_id == (scenario_id or sl.scenario_id),
                )
            )
            if existing and existing > 0:
                continue
            new_line = BudgetLine(
                department_id=sl.department_id,
                account_code=sl.account_code,
                account_name=sl.account_name,
                period=sl.period,
                planned_amount=round(sl.planned_amount * (1 + adjustment_pct / 100), 2),
                currency=sl.currency,
                pnl_category=sl.pnl_category,
                sort_order=sl.sort_order,
                plan_type=PlanType.forecast,
                scenario_id=scenario_id or sl.scenario_id,
                created_by=user_id,
            )
            db.add(new_line)
            await db.flush()
            await BudgetService._write_audit(db, user_id, "budget_line.create_forecast", new_line, {
                "source_id": sl.id,
                "adjustment_pct": adjustment_pct,
            })
            created += 1
        await db.commit()
        return {"created": created}

    @staticmethod
    async def list_comments(db: AsyncSession, line_id: str, page: int, limit: int) -> dict:
        count = await db.scalar(
            select(func.count(BudgetLineComment.id)).where(
                BudgetLineComment.budget_line_id == line_id
            )
        ) or 0

        result = await db.execute(
            select(BudgetLineComment).where(
                BudgetLineComment.budget_line_id == line_id
            ).order_by(BudgetLineComment.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        comments = result.scalars().all()

        items = []
        for c in comments:
            user_name = None
            if c.user:
                user_name = c.user.name if hasattr(c.user, 'name') else c.user.email
            items.append({
                "id": c.id,
                "budget_line_id": c.budget_line_id,
                "user_id": c.user_id,
                "user_name": user_name,
                "text": c.text,
                "created_at": c.created_at.isoformat(),
            })
        return {
            "items": items,
            "total": count,
            "page": page,
            "limit": limit,
            "pages": math.ceil(count / limit) if count > 0 else 1,
        }

    @staticmethod
    async def add_comment(db: AsyncSession, line_id: str, text: str, user_id: str) -> dict:
        line = await db.get(BudgetLine, line_id)
        if not line:
            raise NotFoundError("Budget line not found")
        comment = BudgetLineComment(
            budget_line_id=line_id,
            user_id=user_id,
            text=text,
        )
        db.add(comment)
        await db.flush()
        await BudgetService._write_audit(db, user_id, "budget_line.comment", line, {
            "comment_id": comment.id,
            "text": text[:100],
        })
        await db.commit()
        await db.refresh(comment)
        user_name = None
        if comment.user:
            user_name = comment.user.name if hasattr(comment.user, 'name') else comment.user.email
        return {
            "id": comment.id,
            "budget_line_id": comment.budget_line_id,
            "user_id": comment.user_id,
            "user_name": user_name,
            "text": comment.text,
            "created_at": comment.created_at.isoformat(),
        }

    @staticmethod
    async def get_comment_counts(db: AsyncSession, line_ids: list[str]) -> dict[str, int]:
        if not line_ids:
            return {}
        result = await db.execute(
            select(
                BudgetLineComment.budget_line_id,
                func.count(BudgetLineComment.id)
            ).where(
                BudgetLineComment.budget_line_id.in_(line_ids)
            ).group_by(BudgetLineComment.budget_line_id)
        )
        return {row[0]: row[1] for row in result.all()}
