export interface MonthlyReport {
  year: number;
  month: number;
  invoice_count: number;
  total_net: number;
  total_vat: number;
  total_gross: number;
}

export interface VatReportEntry {
  rate: number;
  count: number;
  net: number;
  vat: number;
  gross: number;
}

export interface VatReport {
  year: number;
  by_vat_rate: VatReportEntry[];
}

export interface DashboardStats {
  total_invoices: number;
  approved: number;
  pending_review: number;
  errors: number;
  total_amount: number;
}

export interface CfoKpis {
  revenue: { current: number; previous: number; trend_pct: number };
  ebitda: { current: number; previous: number; trend_pct: number };
  net_income: { current: number; previous: number; trend_pct: number };
  current_period: string;
}

export interface TrendDataPoint {
  period: string;
  revenue_plan: number;
  revenue_actual: number;
  ebitda_plan: number;
  ebitda_actual: number;
}

export interface DepartmentComparison {
  department_name: string;
  planned: number;
  actual: number;
  variance: number;
  variance_pct: number;
}

export interface BudgetAlert {
  account_name: string;
  department_name: string | null;
  period: string;
  planned: number;
  actual: number;
  overage_pct: number;
}
