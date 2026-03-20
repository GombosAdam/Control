import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';
import { formatDateTime } from '../../../utils/formatters';

export function AuditPage() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => { adminApi.auditLog({ limit: 50 }).then(data => setLogs(data.items)); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('admin.audit')}</h1>
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {['Action', 'Entity', 'User', 'IP', 'Time'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.map((log: any) => (
              <tr key={log.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{log.action}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{log.entity_type} {log.entity_id}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{log.user_id || '-'}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{log.ip_address || '-'}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{formatDateTime(log.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
