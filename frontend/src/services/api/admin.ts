import api from './client';

export const adminApi = {
  listUsers: (params?: { page?: number; limit?: number }) =>
    api.get('/admin/users', { params }).then(r => r.data),

  createUser: (data: { email: string; password: string; full_name: string; role: string }) =>
    api.post('/admin/users', data).then(r => r.data),

  updateUser: (id: string, data: any) =>
    api.put(`/admin/users/${id}`, data).then(r => r.data),

  deleteUser: (id: string) =>
    api.delete(`/admin/users/${id}`).then(r => r.data),

  getSettings: () =>
    api.get('/admin/settings').then(r => r.data),

  updateSetting: (key: string, value: string) =>
    api.put(`/admin/settings/${key}`, { value }).then(r => r.data),

  systemHealth: () =>
    api.get('/admin/system').then(r => r.data),

  auditLog: (params?: { page?: number; limit?: number }) =>
    api.get('/admin/audit', { params }).then(r => r.data),

  gpuStatus: () =>
    api.get('/admin/gpu/status').then(r => r.data),

  gpuStart: () =>
    api.post('/admin/gpu/start').then(r => r.data),

  gpuStop: () =>
    api.post('/admin/gpu/stop').then(r => r.data),

  getPermissionMatrix: () =>
    api.get('/admin/permissions/matrix').then(r => r.data),

  updatePermission: (data: { role: string; permission_id: string; granted: boolean }) =>
    api.put('/admin/permissions/matrix', data).then(r => r.data),
};
