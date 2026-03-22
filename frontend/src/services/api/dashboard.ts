import api from './client';
import type { DashboardStats, CfoKpis, TrendDataPoint, DepartmentComparison, BudgetAlert } from '../../types/report';

export const dashboardApi = {
  getStats: () =>
    api.get<DashboardStats>('/dashboard/stats').then(r => r.data),

  getRecent: (limit: number = 10) =>
    api.get('/dashboard/recent', { params: { limit } }).then(r => r.data),

  getProcessingStatus: () =>
    api.get('/dashboard/processing-status').then(r => r.data),

  getCfoKpis: (params?: { scenario_id?: string; plan_type?: string }) =>
    api.get<CfoKpis>('/dashboard/cfo-kpis', { params }).then(r => r.data),

  getCfoTrends: (params?: { scenario_id?: string; plan_type?: string; periods?: number }) =>
    api.get<TrendDataPoint[]>('/dashboard/cfo-trends', { params }).then(r => r.data),

  getCfoDepartments: (params?: { period?: string; scenario_id?: string; plan_type?: string }) =>
    api.get<DepartmentComparison[]>('/dashboard/cfo-departments', { params }).then(r => r.data),

  getCfoAlerts: (params?: { threshold_pct?: number; scenario_id?: string; plan_type?: string }) =>
    api.get<BudgetAlert[]>('/dashboard/cfo-alerts', { params }).then(r => r.data),
};
