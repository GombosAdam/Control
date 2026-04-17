import { api } from './client';

export interface NavConfig {
  id: string;
  company_tax_number: string;
  company_name: string;
  login: string;
  environment: string;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NavSyncLog {
  id: string;
  nav_config_id: string;
  direction: string;
  date_from: string | null;
  date_to: string | null;
  invoices_found: number;
  invoices_created: number;
  invoices_skipped: number;
  status: string;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface NavTransaction {
  id: string;
  nav_config_id: string;
  invoice_id: string | null;
  transaction_id: string | null;
  operation: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
  invoice_number: string | null;
  retry_count: number;
  request_xml?: string | null;
  response_xml?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaxpayerResult {
  tax_number: string;
  valid: boolean | null;
  name: string | null;
  short_name?: string | null;
  city?: string | null;
}

export const navApi = {
  // Config
  listConfigs: (params?: { page?: number; limit?: number }) =>
    api.get('/nav/config', { params }).then(r => r.data),

  createConfig: (data: {
    company_tax_number: string;
    company_name: string;
    login: string;
    password: string;
    signature_key: string;
    replacement_key: string;
    environment?: string;
  }) => api.post('/nav/config', data).then(r => r.data),

  updateConfig: (id: string, data: Record<string, any>) =>
    api.put(`/nav/config/${id}`, data).then(r => r.data),

  deleteConfig: (id: string) =>
    api.delete(`/nav/config/${id}`).then(r => r.data),

  testConnection: (id: string) =>
    api.post(`/nav/config/${id}/test`).then(r => r.data),

  // Sync
  startSync: (data: { config_id: string; date_from: string; date_to: string }) =>
    api.post('/nav/sync/start', data).then(r => r.data),

  listSyncLogs: (params?: { page?: number; limit?: number }) =>
    api.get('/nav/sync/logs', { params }).then(r => r.data),

  getSyncLog: (id: string) =>
    api.get(`/nav/sync/logs/${id}`).then(r => r.data),

  // Submit
  submitInvoice: (data: { invoice_id: string; config_id: string }) =>
    api.post('/nav/submit', data).then(r => r.data),

  submitBatch: (data: { invoice_ids: string[]; config_id: string }) =>
    api.post('/nav/submit/batch', data).then(r => r.data),

  // Taxpayer
  validateTaxNumber: (data: { config_id: string; tax_number: string }) =>
    api.post<TaxpayerResult>('/nav/taxpayer/validate', data).then(r => r.data),

  validatePartner: (partnerId: string, data: { config_id: string }) =>
    api.post(`/nav/taxpayer/validate-partner/${partnerId}`, data).then(r => r.data),

  // Transactions
  listTransactions: (params?: { page?: number; limit?: number; status?: string }) =>
    api.get('/nav/transactions', { params }).then(r => r.data),

  getTransaction: (id: string) =>
    api.get<NavTransaction>(`/nav/transactions/${id}`).then(r => r.data),

  refreshTransactionStatus: (id: string) =>
    api.post(`/nav/transactions/${id}/refresh`).then(r => r.data),
};
