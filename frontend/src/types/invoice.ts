export type InvoiceStatus =
  | 'uploaded'
  | 'ocr_processing'
  | 'ocr_done'
  | 'extracting'
  | 'pending_review'
  | 'in_approval'
  | 'approved'
  | 'awaiting_match'
  | 'matched'
  | 'posted'
  | 'rejected'
  | 'error';

export interface Invoice {
  id: string;
  invoice_number: string | null;
  partner_id: string | null;
  partner_name: string | null;
  status: InvoiceStatus;
  invoice_date: string | null;
  fulfillment_date: string | null;
  due_date: string | null;
  payment_method: string | null;
  net_amount: number | null;
  vat_rate: number | null;
  vat_amount: number | null;
  gross_amount: number | null;
  currency: string;
  original_filename: string;
  ocr_confidence: number | null;
  is_duplicate: boolean;
  similarity_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface InvoiceLine {
  id: string;
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  net_amount: number | null;
  vat_rate: number | null;
  vat_amount: number | null;
  gross_amount: number | null;
  sort_order: number;
}

export interface InvoiceDetail extends Invoice {
  stored_filepath: string;
  ocr_text: string | null;
  duplicate_of_id: string | null;
  reviewed_by_id: string | null;
  uploaded_by_id: string | null;
  lines: InvoiceLine[];
  extraction_result: ExtractionResult | null;
}

export interface ExtractionResult {
  id: string;
  extracted_data: Record<string, any> | null;
  confidence_scores: Record<string, number> | null;
  model_used: string | null;
  extraction_time_ms: number | null;
}

export interface InvoiceApprovalStep {
  id: string;
  step: number;
  step_name: string;
  status: 'pending' | 'waiting' | 'approved' | 'rejected' | 'cancelled';
  assigned_role: string;
  decided_by: string | null;
  decider_name: string | null;
  decided_at: string | null;
  comment: string | null;
  created_at: string;
}

export interface ApprovalQueueItem {
  invoice_id: string;
  invoice_number: string | null;
  original_filename: string | null;
  gross_amount: number | null;
  currency: string;
  step: number;
  step_name: string;
  assigned_role: string;
  created_at: string;
}
