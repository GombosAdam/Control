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

  delete: (id: string) =>
    api.delete(`/departments/${id}`).then(r => r.data),

  getBudgetMaster: (deptId: string) =>
    api.get(`/departments/${deptId}/budget-master`).then(r => r.data),

  setBudgetMaster: (deptId: string, entries: { account_code: string; account_name: string; is_active?: boolean }[]) =>
    api.put(`/departments/${deptId}/budget-master`, { entries }).then(r => r.data),
};
