import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';
import { formatDateTime } from '../../../utils/formatters';

export function UsersPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => { adminApi.listUsers().then(data => setUsers(data.items)); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('admin.users')}</h1>
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Name', 'Email', 'Role', 'Active', 'Last Login'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u: any) => (
              <tr key={u.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 500 }}>{u.full_name}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{u.email}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500,
                    background: u.role === 'admin' ? '#fee2e2' : '#e0e7ff',
                    color: u.role === 'admin' ? '#dc2626' : '#4338ca',
                  }}>{u.role}</span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                  <span style={{ color: u.is_active ? '#10B981' : '#EF4444' }}>{u.is_active ? 'Yes' : 'No'}</span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{formatDateTime(u.last_login)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
