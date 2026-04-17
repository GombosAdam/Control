import api from './client';

export const positionsApi = {
  list: () =>
    api.get('/positions/').then(r => r.data),

  get: (id: string) =>
    api.get(`/positions/${id}`).then(r => r.data),

  create: (data: { name: string; department_id: string; reports_to_id?: string }) =>
    api.post('/positions/', data).then(r => r.data),

  update: (id: string, data: { name?: string; department_id?: string; reports_to_id?: string }) =>
    api.put(`/positions/${id}`, data).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/positions/${id}`).then(r => r.data),
};
