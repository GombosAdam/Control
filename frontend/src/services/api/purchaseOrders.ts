import api from './client';

export const purchaseOrdersApi = {
  list: (params?: { department_id?: string; status?: string; page?: number; limit?: number }) =>
    api.get('/purchase-orders/', { params }).then(r => r.data),

  create: (data: {
    po_number?: string; department_id: string; budget_line_id: string;
    partner_id?: string; supplier_name: string; supplier_tax_id?: string;
    lines: { description: string; quantity: number; unit_price: number }[];
    currency?: string; accounting_code: string; description?: string;
  }) =>
    api.post('/purchase-orders/', data).then(r => r.data),

  update: (id: string, data: { supplier_name?: string; supplier_tax_id?: string; amount?: number; description?: string }) =>
    api.put(`/purchase-orders/${id}`, data).then(r => r.data),

  approve: (id: string) =>
    api.post(`/purchase-orders/${id}/approve`).then(r => r.data),

  receive: (id: string, data?: { received_date: string; notes?: string }) =>
    api.post(`/purchase-orders/${id}/receive`, data || {}).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/purchase-orders/${id}`).then(r => r.data),

  getApprovals: (id: string) =>
    api.get(`/purchase-orders/${id}/approvals`).then(r => r.data),

  getGoodsReceipt: (id: string) =>
    api.get(`/purchase-orders/${id}/goods-receipt`).then(r => r.data),

  decideApproval: (poId: string, step: number, decision: 'approved' | 'rejected', comment?: string) =>
    api.post(`/purchase-orders/${poId}/approvals/${step}/decide`, { decision, comment }).then(r => r.data),
};
