import api from './client';
import type { PaginatedResponse } from '../../types/api';
import type { Partner } from '../../types/partner';

export const partnersApi = {
  list: (params?: { page?: number; limit?: number; partner_type?: string; search?: string }) =>
    api.get<PaginatedResponse<Partner>>('/partners', { params }).then(r => r.data),

  get: (id: string) =>
    api.get<Partner>(`/partners/${id}`).then(r => r.data),

  create: (data: Partial<Partner>) =>
    api.post('/partners', data).then(r => r.data),

  update: (id: string, data: Partial<Partner>) =>
    api.put(`/partners/${id}`, data).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/partners/${id}`).then(r => r.data),

  getInvoices: (id: string) =>
    api.get(`/partners/${id}/invoices`).then(r => r.data),
};
