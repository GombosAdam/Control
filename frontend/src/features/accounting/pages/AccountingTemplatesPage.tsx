import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, Plus, Trash2, Save } from 'lucide-react';
import { accountingApi } from '../../../services/api/accounting';

interface Template {
  id: string;
  account_code_pattern: string;
  name: string;
  debit_account: string;
  credit_account: string;
  description: string | null;
}

export function AccountingTemplatesPage() {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ account_code_pattern: '', name: '', debit_account: '', credit_account: '', description: '' });

  const load = () => { accountingApi.listTemplates().then(setTemplates); };
  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    await accountingApi.createTemplate(form);
    setForm({ account_code_pattern: '', name: '', debit_account: '', credit_account: '', description: '' });
    setShowAdd(false);
    load();
  };

  const handleDelete = async (id: string) => {
    await accountingApi.deleteTemplate(id);
    load();
  };

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
          <BookOpen size={20} style={{ color: '#0EA5E9' }} />
          {t('accounting_templates.title')}
        </h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
            background: '#0EA5E9', color: '#fff', borderRadius: '6px', border: 'none',
            fontSize: '13px', fontWeight: 500, cursor: 'pointer',
          }}
        >
          <Plus size={14} /> {t('accounting_templates.add')}
        </button>
      </div>

      {showAdd && (
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px', marginBottom: '12px' }}>
            <input placeholder={t('accounting_templates.pattern')} value={form.account_code_pattern}
              onChange={e => setForm({ ...form, account_code_pattern: e.target.value })}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '13px' }} />
            <input placeholder={t('accounting_templates.name')} value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '13px' }} />
            <input placeholder={t('accounting_templates.debit')} value={form.debit_account}
              onChange={e => setForm({ ...form, debit_account: e.target.value })}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '13px' }} />
            <input placeholder={t('accounting_templates.credit')} value={form.credit_account}
              onChange={e => setForm({ ...form, credit_account: e.target.value })}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '13px' }} />
            <input placeholder={t('accounting_templates.description')} value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '13px' }} />
          </div>
          <button onClick={handleAdd} disabled={!form.account_code_pattern || !form.name || !form.debit_account || !form.credit_account}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
              background: '#10B981', color: '#fff', borderRadius: '6px', border: 'none',
              fontSize: '13px', fontWeight: 500, cursor: 'pointer',
              opacity: !form.account_code_pattern || !form.name ? 0.5 : 1,
            }}>
            <Save size={14} /> {t('common.save')}
          </button>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {[t('accounting_templates.pattern'), t('accounting_templates.name'), t('accounting_templates.debit'), t('accounting_templates.credit'), t('accounting_templates.description'), ''].map(h => (
              <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#666', fontSize: '11px', textTransform: 'uppercase' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {templates.map(t => (
            <tr key={t.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 600 }}>{t.account_code_pattern}</td>
              <td style={{ padding: '10px 12px' }}>{t.name}</td>
              <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#DC2626' }}>{t.debit_account}</td>
              <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#059669' }}>{t.credit_account}</td>
              <td style={{ padding: '10px 12px', color: '#666' }}>{t.description}</td>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => handleDelete(t.id)} style={{
                  background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444', padding: '4px',
                }}>
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {templates.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('accounting_templates.empty')}</div>}
    </div>
  );
}
