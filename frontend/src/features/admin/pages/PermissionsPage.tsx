import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Check } from 'lucide-react';
import { adminApi } from '../../../services/api/admin';

interface PermissionItem {
  id: string;
  resource: string;
  action: string;
  description: string;
}

interface MatrixData {
  roles: string[];
  permissions: PermissionItem[];
  granted: Record<string, string[]>;
}

const roleLabels: Record<string, string> = {
  admin: 'Admin',
  cfo: 'CFO',
  department_head: 'Vez.',
  accountant: 'Könyv.',
  reviewer: 'Ell.',
  clerk: 'Ügyint.',
};

const roleColors: Record<string, string> = {
  admin: '#EF4444',
  cfo: '#F59E0B',
  department_head: '#3B82F6',
  accountant: '#10B981',
  reviewer: '#8B5CF6',
  clerk: '#6B7280',
};

export function PermissionsPage() {
  const { t } = useTranslation();
  const [matrix, setMatrix] = useState<MatrixData | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await adminApi.getPermissionMatrix();
      setMatrix(data);
    } catch {
      setMatrix(null);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleToggle = async (role: string, permId: string, currentlyGranted: boolean) => {
    if (role === 'admin') return; // admin always has everything
    const key = `${role}:${permId}`;
    setToggling(key);
    try {
      await adminApi.updatePermission({ role, permission_id: permId, granted: !currentlyGranted });
      // Update local state
      setMatrix(prev => {
        if (!prev) return prev;
        const newGranted = { ...prev.granted };
        const rolePerms = [...(newGranted[role] || [])];
        if (!currentlyGranted) {
          rolePerms.push(permId);
        } else {
          const idx = rolePerms.indexOf(permId);
          if (idx >= 0) rolePerms.splice(idx, 1);
        }
        newGranted[role] = rolePerms;
        return { ...prev, granted: newGranted };
      });
    } catch { }
    setToggling(null);
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.loading')}</div>;
  if (!matrix) return <div style={{ padding: '40px', textAlign: 'center', color: '#EF4444' }}>Failed to load permissions</div>;

  // Group permissions by resource prefix
  const groups: Record<string, PermissionItem[]> = {};
  for (const perm of matrix.permissions) {
    const group = perm.resource.split('.')[0];
    (groups[group] ||= []).push(perm);
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <Shield size={20} color="#6B7280" />
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>{t('admin.permissionsTitle')}</h1>
          <p style={{ fontSize: '13px', color: '#888', margin: '2px 0 0' }}>{t('admin.permissionsDesc')}</p>
        </div>
      </div>

      <div style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
              <th style={{ padding: '10px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#888', textTransform: 'uppercase', minWidth: '200px', position: 'sticky', left: 0, background: '#f9fafb', zIndex: 1 }}>
                Jogosultság
              </th>
              <th style={{ padding: '10px 8px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#888', minWidth: '160px' }}>
                Leírás
              </th>
              {matrix.roles.map(role => (
                <th key={role} style={{ padding: '10px 6px', textAlign: 'center', minWidth: '60px' }}>
                  <div style={{
                    display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                    background: roleColors[role] || '#6B7280', color: '#fff',
                    fontSize: '10px', fontWeight: 700,
                  }}>
                    {roleLabels[role] || role}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(groups).map(([group, perms]) => (
              <>
                {/* Group header */}
                <tr key={`g-${group}`}>
                  <td colSpan={2 + matrix.roles.length} style={{
                    padding: '8px 14px', background: '#f0f4f8', fontWeight: 700,
                    fontSize: '11px', color: '#374151', textTransform: 'uppercase',
                    borderBottom: '1px solid #e5e7eb', borderTop: '1px solid #e5e7eb',
                  }}>
                    {group}
                  </td>
                </tr>
                {/* Permission rows */}
                {perms.map(perm => (
                  <tr key={perm.id} style={{ borderBottom: '1px solid #f0f0f0' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#fafbfc'}
                    onMouseLeave={e => e.currentTarget.style.background = ''}
                  >
                    <td style={{
                      padding: '8px 14px', fontWeight: 500, color: '#333',
                      position: 'sticky', left: 0, background: 'inherit', zIndex: 1,
                    }}>
                      <code style={{ fontSize: '11px', color: '#06B6D4' }}>{perm.resource}</code>
                      <span style={{ color: '#999', margin: '0 4px' }}>:</span>
                      <code style={{ fontSize: '11px', color: '#F97316' }}>{perm.action}</code>
                    </td>
                    <td style={{ padding: '8px 8px', color: '#888', fontSize: '11px' }}>
                      {perm.description}
                    </td>
                    {matrix.roles.map(role => {
                      const isGranted = role === 'admin' || (matrix.granted[role] || []).includes(perm.id);
                      const isAdmin = role === 'admin';
                      const key = `${role}:${perm.id}`;
                      const isToggling = toggling === key;
                      return (
                        <td key={role} style={{ padding: '4px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleToggle(role, perm.id, isGranted)}
                            disabled={isAdmin || isToggling}
                            style={{
                              width: '28px', height: '28px', borderRadius: '6px',
                              border: isGranted ? 'none' : '2px solid #d1d5db',
                              background: isGranted ? (isAdmin ? '#9CA3AF' : '#10B981') : '#fff',
                              cursor: isAdmin ? 'default' : 'pointer',
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                              opacity: isToggling ? 0.5 : 1,
                              transition: 'all 150ms',
                            }}
                          >
                            {isGranted && <Check size={14} color="#fff" strokeWidth={3} />}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
