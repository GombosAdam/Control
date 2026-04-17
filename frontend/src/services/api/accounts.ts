import api from './client';
import type { AccountMaster } from '../../types/controlling';

export const accountsApi = {
  list: (params?: { type?: string; active?: boolean; pnl_category?: string }) =>
    api.get<AccountMaster[]>('/accounts/', { params }).then(r => r.data),

  tree: () =>
    api.get<AccountMaster[]>('/accounts/tree').then(r => r.data),

  get: (code: string) =>
    api.get<AccountMaster & { children: AccountMaster[] }>(`/accounts/${code}`).then(r => r.data),
};
