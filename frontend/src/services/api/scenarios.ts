import api from './client';
import type { Scenario } from '../../types/controlling';

export const scenariosApi = {
  list: () =>
    api.get<Scenario[]>('/scenarios').then(r => r.data),

  create: (data: { name: string; description?: string }) =>
    api.post<Scenario>('/scenarios', data).then(r => r.data),

  copy: (data: { source_scenario_id: string; name: string; description?: string; adjustment_pct?: number; period?: string; department_id?: string }) =>
    api.post('/scenarios/copy', data).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/scenarios/${id}`).then(r => r.data),
};
