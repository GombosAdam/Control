import api from './client';

export const accountingApi = {
  listInvoices: (params?: { page?: number; limit?: number; search?: string; currency?: string }) =>
    api.get('/accounting/invoices', { params }).then(r => r.data),

  getSummary: () =>
    api.get('/accounting/summary').then(r => r.data),

  listEntries: (params?: { page?: number; limit?: number; period?: string; department_id?: string; account_code?: string; invoice_id?: string }) =>
    api.get('/accounting/entries', { params }).then(r => r.data),

  listTemplates: () =>
    api.get('/accounting/templates').then(r => r.data),

  createTemplate: (data: { account_code_pattern: string; name: string; debit_account: string; credit_account: string; description?: string }) =>
    api.post('/accounting/templates', data).then(r => r.data),

  updateTemplate: (id: string, data: Partial<{ account_code_pattern: string; name: string; debit_account: string; credit_account: string; description: string }>) =>
    api.put(`/accounting/templates/${id}`, data).then(r => r.data),

  deleteTemplate: (id: string) =>
    api.delete(`/accounting/templates/${id}`).then(r => r.data),
};
