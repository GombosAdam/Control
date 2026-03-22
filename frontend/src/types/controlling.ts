export interface Department {
  id: string;
  name: string;
  code: string;
  parent_id: string | null;
  manager_id: string | null;
  manager_name: string | null;
  created_at: string;
  updated_at: string;
}

export type BudgetStatus = 'draft' | 'approved' | 'locked';

export interface BudgetLine {
  id: string;
  department_id: string;
  department_name: string | null;
  account_code: string;
  account_name: string;
  period: string;
  planned_amount: number;
  currency: string;
  status: BudgetStatus;
  created_by: string;
  creator_name: string | null;
  approved_by: string | null;
  approver_name: string | null;
  committed?: number;
  actual?: number;
  available?: number;
  pnl_category?: string;
  plan_type?: 'budget' | 'forecast';
  scenario_id?: string | null;
  scenario_name?: string | null;
  created_at: string;
  updated_at: string;
}

export type POStatus = 'draft' | 'approved' | 'received' | 'closed' | 'cancelled';

export interface PurchaseOrder {
  id: string;
  po_number: string;
  department_id: string;
  department_name: string | null;
  budget_line_id: string;
  budget_line_name: string | null;
  supplier_name: string;
  supplier_tax_id: string | null;
  amount: number;
  currency: string;
  accounting_code: string;
  description: string | null;
  status: POStatus;
  created_by: string;
  approved_by: string | null;
  created_at: string;
  updated_at: string;
}

export type MatchStatus = 'unmatched' | 'matched' | 'mismatch' | 'posted';

export interface AccountingEntry {
  id: string;
  invoice_id: string;
  purchase_order_id: string | null;
  po_number: string | null;
  account_code: string;
  department_id: string;
  department_name: string | null;
  amount: number;
  currency: string;
  period: string;
  entry_type: 'debit' | 'credit';
  posted_at: string;
  posted_by: string | null;
}

export interface PlanVsActual {
  department_id: string;
  department_name: string | null;
  account_code: string;
  account_name: string;
  period: string;
  planned: number;
  actual: number;
  committed: number;
  variance: number;
  variance_pct: number;
  currency: string;
}

export interface BudgetStatusReport {
  department_id: string;
  department_name: string;
  department_code: string;
  planned: number;
  committed: number;
  spent: number;
  available: number;
  utilization_pct: number;
}

export interface EbitdaReport {
  department_id: string;
  department_name: string;
  planned_budget: number;
  actual_cost: number;
  ebitda: number;
  margin_pct: number;
}

export interface CommitmentReport {
  id: string;
  po_number: string;
  department_name: string | null;
  supplier_name: string;
  amount: number;
  currency: string;
  accounting_code: string;
  status: string;
  created_at: string;
}

export type PnlCategory = 'revenue' | 'cogs' | 'opex' | 'depreciation' | 'interest' | 'tax';

export interface PnlChildLine {
  id: string;
  account_code: string;
  account_name: string;
  department_name: string | null;
  planned: number;
  actual: number;
  variance: number;
  variance_pct: number;
  status: BudgetStatus;
  created_by: string;
  creator_name: string | null;
  approved_by: string | null;
  approver_name: string | null;
  updated_at: string;
  plan_type?: 'budget' | 'forecast';
  scenario_id?: string | null;
  comment_count?: number;
}

export interface PnlRow {
  key: string;
  label: string;
  is_subtotal: boolean;
  is_editable: boolean;
  planned: number;
  actual: number;
  variance: number;
  variance_pct: number;
  margin_pct: number;
  children: PnlChildLine[];
}

export interface PnlWaterfall {
  rows: PnlRow[];
  structure: { key: string; label: string; is_subtotal: boolean }[];
}

export interface BulkActionResult {
  approved?: string[];
  locked?: string[];
  adjusted?: string[];
  errors: { id: string; reason: string }[];
}

export interface ValidationResult {
  valid: string[];
  invalid: { id: string; reasons: string[] }[];
  warnings: { id: string; warnings: string[] }[];
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, any> | null;
  created_at: string;
}

export interface BudgetLineComment {
  id: string;
  budget_line_id: string;
  user_id: string;
  user_name: string | null;
  text: string;
  created_at: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  created_by: string;
  creator_name: string | null;
  created_at: string;
}
