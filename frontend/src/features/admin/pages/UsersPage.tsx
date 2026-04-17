import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';
import { departmentsApi } from '../../../services/api/departments';
import { positionsApi } from '../../../services/api/positions';
import { formatDateTime } from '../../../utils/formatters';

interface Department {
  id: string;
  name: string;
  code: string;
}

interface Position {
  id: string;
  name: string;
  department_id: string;
  department_name: string | null;
}

export function UsersPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<any[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);

  useEffect(() => {
    Promise.all([
      adminApi.listUsers({ limit: 200 }).then(data => setUsers(data.items)),
      departmentsApi.list().then(setDepartments),
      positionsApi.list().then(setPositions),
    ]);
  }, []);

  const handleDeptChange = async (userId: string, deptId: string) => {
    await adminApi.updateUser(userId, { department_id: deptId || null });
    const data = await adminApi.listUsers({ limit: 200 });
    setUsers(data.items);
  };

  const handleRoleChange = async (userId: string, role: string) => {
    await adminApi.updateUser(userId, { role });
    const data = await adminApi.listUsers({ limit: 200 });
    setUsers(data.items);
  };

  const handlePositionChange = async (userId: string, positionId: string) => {
    await adminApi.updateUser(userId, { position_id: positionId || null });
    const data = await adminApi.listUsers({ limit: 200 });
    setUsers(data.items);
  };

  const roleColors: Record<string, { bg: string; color: string }> = {
    admin: { bg: '#fee2e2', color: '#dc2626' },
    cfo: { bg: '#fef3c7', color: '#92400e' },
    department_head: { bg: '#d1fae5', color: '#065f46' },
    clerk: { bg: '#fce7f3', color: '#9d174d' },
    accountant: { bg: '#e0e7ff', color: '#4338ca' },
    reviewer: { bg: '#e0e7ff', color: '#4338ca' },
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('admin.users')}</h1>
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Name', 'Email', 'Role', 'Department', 'Pozíció', 'Active', 'Last Login'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u: any) => {
              const rc = roleColors[u.role] || roleColors.reviewer;
              return (
                <tr key={u.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 500 }}>{u.full_name}</td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{u.email}</td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    <select
                      value={u.role}
                      onChange={e => handleRoleChange(u.id, e.target.value)}
                      style={{
                        padding: '2px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 500,
                        border: '1px solid #e5e7eb', cursor: 'pointer',
                        background: rc.bg, color: rc.color,
                      }}
                    >
                      {['admin', 'cfo', 'department_head', 'clerk', 'accountant', 'reviewer'].map(r => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    <select
                      value={u.department_id || ''}
                      onChange={e => handleDeptChange(u.id, e.target.value)}
                      style={{
                        padding: '4px 8px', borderRadius: '6px', fontSize: '12px',
                        border: '1px solid #e5e7eb', cursor: 'pointer', background: '#fff',
                        color: u.department_id ? '#333' : '#999',
                      }}
                    >
                      <option value="">— Nincs —</option>
                      {departments.map(d => (
                        <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                      ))}
                    </select>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    <select
                      value={u.position_id || ''}
                      onChange={e => handlePositionChange(u.id, e.target.value)}
                      style={{
                        padding: '4px 8px', borderRadius: '6px', fontSize: '12px',
                        border: '1px solid #e5e7eb', cursor: 'pointer', background: '#fff',
                        color: u.position_id ? '#333' : '#999',
                      }}
                    >
                      <option value="">— Nincs —</option>
                      {positions.map(p => (
                        <option key={p.id} value={p.id}>{p.name} ({p.department_name})</option>
                      ))}
                    </select>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                    <span style={{ color: u.is_active ? '#10B981' : '#EF4444' }}>{u.is_active ? 'Yes' : 'No'}</span>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{formatDateTime(u.last_login)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
