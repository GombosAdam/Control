import api from './client';
import type { DashboardStats } from '../../types/report';

export const dashboardApi = {
  getStats: () =>
    api.get<DashboardStats>('/dashboard/stats').then(r => r.data),

  getRecent: (limit: number = 10) =>
    api.get('/dashboard/recent', { params: { limit } }).then(r => r.data),

  getProcessingStatus: () =>
    api.get('/dashboard/processing-status').then(r => r.data),
};
