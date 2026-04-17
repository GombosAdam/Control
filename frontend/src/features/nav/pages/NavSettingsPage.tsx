import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { navApi, NavConfig } from '../../../services/api/nav';
import { Plus, Trash2, TestTube, CheckCircle, XCircle } from 'lucide-react';

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', border: '1px solid #d1d5db',
  borderRadius: '6px', fontSize: '14px', boxSizing: 'border-box',
};

const btnStyle: React.CSSProperties = {
  padding: '8px 16px', borderRadius: '6px', border: 'none',
  cursor: 'pointer', fontSize: '14px', fontWeight: 500,
};

export function NavSettingsPage() {
  const { t } = useTranslation();
  const [configs, setConfigs] = useState<NavConfig[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [form, setForm] = useState({
    company_tax_number: '', company_name: '', login: '',
    password: '', signature_key: '', replacement_key: '', environment: 'test',
  });

  const load = () => {
    navApi.listConfigs({ limit: 50 }).then(data => setConfigs(data.items || []));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    await navApi.createConfig(form);
    setShowForm(false);
    setForm({ company_tax_number: '', company_name: '', login: '', password: '', signature_key: '', replacement_key: '', environment: 'test' });
    load();
  };

  const handleDelete = async (id: string) => {
    if (confirm(t('navSettings.confirmDelete'))) {
      await navApi.deleteConfig(id);
      load();
    }
  };

  const handleTest = async (id: string) => {
    setTestResults(prev => ({ ...prev, [id]: { success: false, message: '...' } }));
    try {
      const result = await navApi.testConnection(id);
      setTestResults(prev => ({
        ...prev,
        [id]: { success: result.success, message: result.success ? result.taxpayer_name : result.error },
      }));
    } catch (e: any) {
      setTestResults(prev => ({ ...prev, [id]: { success: false, message: e.message } }));
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>{t('navSettings.title')}</h1>
        <button onClick={() => setShowForm(!showForm)} style={{ ...btnStyle, background: '#DC2626', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Plus size={16} /> {t('navSettings.addConfig')}
        </button>
      </div>

      {showForm && (
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>{t('navSettings.newConfig')}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.taxNumber')}</label>
              <input style={inputStyle} value={form.company_tax_number} onChange={e => setForm(f => ({ ...f, company_tax_number: e.target.value }))} placeholder="12345678" />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.companyName')}</label>
              <input style={inputStyle} value={form.company_name} onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.login')}</label>
              <input style={inputStyle} value={form.login} onChange={e => setForm(f => ({ ...f, login: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.password')}</label>
              <input style={inputStyle} type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.signatureKey')}</label>
              <input style={inputStyle} type="password" value={form.signature_key} onChange={e => setForm(f => ({ ...f, signature_key: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.replacementKey')}</label>
              <input style={inputStyle} type="password" value={form.replacement_key} onChange={e => setForm(f => ({ ...f, replacement_key: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>{t('navSettings.environment')}</label>
              <select style={inputStyle} value={form.environment} onChange={e => setForm(f => ({ ...f, environment: e.target.value }))}>
                <option value="test">Test</option>
                <option value="production">Production</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
            <button onClick={handleCreate} style={{ ...btnStyle, background: '#DC2626', color: '#fff' }}>{t('common.save')}</button>
            <button onClick={() => setShowForm(false)} style={{ ...btnStyle, background: '#e5e7eb' }}>{t('common.cancel')}</button>
          </div>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '10px' }}>{t('navSettings.companyName')}</th>
            <th style={{ padding: '10px' }}>{t('navSettings.taxNumber')}</th>
            <th style={{ padding: '10px' }}>{t('navSettings.environment')}</th>
            <th style={{ padding: '10px' }}>{t('navSettings.lastSync')}</th>
            <th style={{ padding: '10px' }}>{t('navSettings.status')}</th>
            <th style={{ padding: '10px' }}>{t('common.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {configs.map(cfg => (
            <tr key={cfg.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '10px', fontWeight: 500 }}>{cfg.company_name}</td>
              <td style={{ padding: '10px', fontFamily: 'monospace' }}>{cfg.company_tax_number}</td>
              <td style={{ padding: '10px' }}>
                <span style={{
                  padding: '2px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 500,
                  background: cfg.environment === 'production' ? '#FEE2E2' : '#DBEAFE',
                  color: cfg.environment === 'production' ? '#DC2626' : '#2563EB',
                }}>
                  {cfg.environment}
                </span>
              </td>
              <td style={{ padding: '10px', fontSize: '13px', color: '#6b7280' }}>
                {cfg.last_sync_at ? new Date(cfg.last_sync_at).toLocaleString('hu-HU') : '-'}
              </td>
              <td style={{ padding: '10px' }}>
                {cfg.is_active
                  ? <span style={{ color: '#16a34a', fontSize: '13px' }}>{t('common.active')}</span>
                  : <span style={{ color: '#dc2626', fontSize: '13px' }}>{t('common.inactive')}</span>}
              </td>
              <td style={{ padding: '10px' }}>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button onClick={() => handleTest(cfg.id)} title={t('navSettings.testConnection')}
                    style={{ ...btnStyle, padding: '6px 10px', background: '#f3f4f6', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <TestTube size={14} /> {t('navSettings.test')}
                  </button>
                  <button onClick={() => handleDelete(cfg.id)} title={t('common.delete')}
                    style={{ ...btnStyle, padding: '6px 10px', background: '#FEE2E2', color: '#DC2626' }}>
                    <Trash2 size={14} />
                  </button>
                  {testResults[cfg.id] && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px' }}>
                      {testResults[cfg.id].success
                        ? <><CheckCircle size={14} color="#16a34a" /> {testResults[cfg.id].message}</>
                        : <><XCircle size={14} color="#dc2626" /> {testResults[cfg.id].message}</>}
                    </span>
                  )}
                </div>
              </td>
            </tr>
          ))}
          {configs.length === 0 && (
            <tr><td colSpan={6} style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>{t('navSettings.noConfigs')}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
