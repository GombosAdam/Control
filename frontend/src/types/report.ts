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
