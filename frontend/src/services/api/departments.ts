import api from './client';

export const departmentsApi = {
  list: () =>
    api.get('/departments/').then(r => r.data),

  get: (id: string) =>
    api.get(`/departments/${id}`).then(r => r.data),

  create: (data: { name: string; code: string; parent_id?: string; manager_id?: string }) =>
    api.post('/departments/', data).then(r => r.data),

  update: (id: string, data: { name?: string; code?: string; parent_id?: string; manager_id?: string }) =>
    api.put(`/departments/${id}`, data).then(r => r.data),
};
