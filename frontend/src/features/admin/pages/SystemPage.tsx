import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';

export function SystemPage() {
  const { t } = useTranslation();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => { adminApi.systemHealth().then(setHealth); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('admin.system')}</h1>
      {health && (
        <div style={{ background: '#fff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          {Object.entries(health).map(([key, value]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ fontWeight: 500 }}>{key}</span>
              <span style={{ color: '#666' }}>{String(value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
