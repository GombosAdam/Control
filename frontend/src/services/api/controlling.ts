import api from './client';

export const controllingApi = {
  planVsActual: (params?: { department_id?: string; period?: string }) =>
    api.get('/controlling/plan-vs-actual', { params }).then(r => r.data),

  budgetStatus: (params?: { department_id?: string }) =>
    api.get('/controlling/budget-status', { params }).then(r => r.data),

  commitment: (params?: { department_id?: string }) =>
    api.get('/controlling/commitment', { params }).then(r => r.data),

  ebitda: (params?: { department_id?: string; period?: string }) =>
    api.get('/controlling/ebitda', { params }).then(r => r.data),

  pnlWaterfall: (params?: { department_id?: string; period?: string; status?: string; period_from?: string; period_to?: string; plan_type?: string; scenario_id?: string }) =>
    api.get('/controlling/pnl', { params }).then(r => r.data),
};
