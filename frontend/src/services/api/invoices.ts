import api from './client';
import type { PaginatedResponse } from '../../types/api';
import type { Invoice, InvoiceDetail } from '../../types/invoice';

export const invoicesApi = {
  list: (params?: { page?: number; limit?: number; status?: string; search?: string }) =>
    api.get<PaginatedResponse<Invoice>>('/invoices', { params }).then(r => r.data),

  get: (id: string) =>
    api.get<InvoiceDetail>(`/invoices/${id}`).then(r => r.data),

  update: (id: string, data: Partial<Invoice>) =>
    api.put(`/invoices/${id}`, data).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/invoices/${id}`).then(r => r.data),

  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/invoices/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  bulkUpload: (files: File[]) => {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    return api.post('/invoices/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  getPdf: (id: string) =>
    api.get(`/invoices/${id}/pdf`, { responseType: 'blob' }).then(r => r.data),

  reprocess: (id: string) =>
    api.post(`/invoices/${id}/reprocess`).then(r => r.data),
};
