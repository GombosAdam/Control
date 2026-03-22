import api from './client';

export const budgetApi = {
  listLines: (params?: { department_id?: string; period?: string; status?: string; page?: number; limit?: number; plan_type?: string; scenario_id?: string }) =>
    api.get('/budget/lines', { params }).then(r => r.data),

  createLine: (data: { department_id: string; account_code: string; account_name: string; period: string; planned_amount: number; currency?: string; pnl_category?: string; plan_type?: string; scenario_id?: string }) =>
    api.post('/budget/lines', data).then(r => r.data),

  updateLine: (id: string, data: { account_code?: string; account_name?: string; planned_amount?: number }) =>
    api.put(`/budget/lines/${id}`, data).then(r => r.data),

  approveLine: (id: string) =>
    api.post(`/budget/lines/${id}/approve`).then(r => r.data),

  lockLine: (id: string) =>
    api.post(`/budget/lines/${id}/lock`).then(r => r.data),

  getPeriods: () =>
    api.get('/budget/periods').then(r => r.data) as Promise<string[]>,

  getAvailability: (deptId: string) =>
    api.get(`/budget/availability/${deptId}`).then(r => r.data),

  getLineAudit: (lineId: string, page = 1, limit = 20) =>
    api.get(`/budget/lines/${lineId}/audit`, { params: { page, limit } }).then(r => r.data),

  bulkApprove: (lineIds: string[]) =>
    api.post('/budget/lines/bulk-approve', { line_ids: lineIds }).then(r => r.data),

  bulkLock: (lineIds: string[]) =>
    api.post('/budget/lines/bulk-lock', { line_ids: lineIds }).then(r => r.data),

  copyPeriod: (data: { source_period: string; target_period: string; department_id?: string }) =>
    api.post('/budget/lines/copy-period', data).then(r => r.data),

  bulkAdjust: (lineIds: string[], percentage: number) =>
    api.post('/budget/lines/bulk-adjust', { line_ids: lineIds, percentage }).then(r => r.data),

  validateApprove: (lineIds: string[]) =>
    api.post('/budget/lines/validate-approve', { line_ids: lineIds }).then(r => r.data),

  createYearPlan: (data: { year: number; source_year?: number; adjustment_pct?: number; department_id?: string; plan_type?: string; scenario_id?: string }) =>
    api.post('/budget/create-year-plan', data).then(r => r.data),

  createForecast: (data: { source_period?: string; department_id?: string; adjustment_pct?: number; scenario_id?: string }) =>
    api.post('/budget/lines/create-forecast', data).then(r => r.data),

  getLineComments: (lineId: string, page = 1, limit = 50) =>
    api.get(`/budget/lines/${lineId}/comments`, { params: { page, limit } }).then(r => r.data),

  addLineComment: (lineId: string, text: string) =>
    api.post(`/budget/lines/${lineId}/comments`, { text }).then(r => r.data),
};
