import api from './client';

export const reconciliationApi = {
  listPending: (params?: { page?: number; limit?: number }) =>
    api.get('/reconciliation/pending', { params }).then(r => r.data),

  autoMatch: (invoiceId: string) =>
    api.post(`/reconciliation/${invoiceId}/match`).then(r => r.data),

  manualMatch: (invoiceId: string, purchaseOrderId: string) =>
    api.post(`/reconciliation/${invoiceId}/manual-match`, { purchase_order_id: purchaseOrderId }).then(r => r.data),

  postToAccounting: (invoiceId: string) =>
    api.post(`/reconciliation/${invoiceId}/post`).then(r => r.data),
};
