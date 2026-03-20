export type PartnerType = 'supplier' | 'customer' | 'both';

export interface Partner {
  id: string;
  name: string;
  tax_number: string | null;
  bank_account: string | null;
  partner_type: PartnerType;
  address: string | null;
  contact_email: string | null;
  auto_detected: boolean;
  invoice_count: number;
  total_amount: number;
  created_at: string;
}
