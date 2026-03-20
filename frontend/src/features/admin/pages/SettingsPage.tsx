import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';

export function SettingsPage() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<any[]>([]);

  useEffect(() => { adminApi.getSettings().then(setSettings); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('admin.settings')}</h1>
      <div style={{ background: '#fff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        {settings.length === 0 && <p style={{ color: '#999' }}>{t('common.noData')}</p>}
        {settings.map((s: any) => (
          <div key={s.key} style={{ padding: '12px 0', borderBottom: '1px solid #f3f4f6' }}>
            <p style={{ fontWeight: 500, margin: 0 }}>{s.key}</p>
            <p style={{ fontSize: '13px', color: '#666', margin: '4px 0 0' }}>{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
