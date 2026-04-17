import api from './client';
import type { TokenResponse } from '../../types/user';

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }).then(r => r.data),

  register: (data: { email: string; password: string; full_name: string; role?: string }) =>
    api.post('/auth/register', data).then(r => r.data),

  me: () => api.get('/auth/me').then(r => r.data),

  refresh: () => api.post('/auth/refresh').then(r => r.data),

  switchUser: (userId: string) =>
    api.post(`/auth/switch-user/${userId}`).then(r => r.data),

  getMyPermissions: () =>
    api.get('/auth/me/permissions').then(r => r.data),
};
