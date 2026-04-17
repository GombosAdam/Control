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
  default_accounting_code: string | null;
  payment_terms_days: number;
  payment_method: string;
  currency: string;
  country_code: string;
  city: string | null;
  zip_code: string | null;
  contact_person: string | null;
  contact_phone: string | null;
  iban: string | null;
  swift_code: string | null;
  is_verified: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
