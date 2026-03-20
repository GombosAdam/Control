import api from './client';

export const extractionApi = {
  getQueue: (params?: { page?: number; limit?: number }) =>
    api.get('/extraction/queue', { params }).then(r => r.data),

  approve: (invoiceId: string) =>
    api.post(`/extraction/${invoiceId}/approve`).then(r => r.data),

  reject: (invoiceId: string) =>
    api.post(`/extraction/${invoiceId}/reject`).then(r => r.data),

  getDuplicates: () =>
    api.get('/extraction/duplicates').then(r => r.data),
};
