import api from './client';

export const reportsApi = {
  monthly: (year?: number, month?: number) =>
    api.get('/reports/monthly', { params: { year, month } }).then(r => r.data),

  vat: (year?: number) =>
    api.get('/reports/vat', { params: { year } }).then(r => r.data),

  suppliers: () =>
    api.get('/reports/suppliers').then(r => r.data),
};
