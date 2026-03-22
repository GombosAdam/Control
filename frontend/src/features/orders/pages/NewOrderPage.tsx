import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle } from 'lucide-react';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { departmentsApi } from '../../../services/api/departments';
import { budgetApi } from '../../../services/api/budget';
import { formatCurrency } from '../../../utils/formatters';
import type { Department, BudgetLine } from '../../../types/controlling';

export function NewOrderPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [budgetLines, setBudgetLines] = useState<BudgetLine[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    department_id: '', budget_line_id: '',
    supplier_name: '', supplier_tax_id: '', amount: 0,
    currency: 'HUF', accounting_code: '', description: '',
  });

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);

  useEffect(() => {
    if (form.department_id) {
      budgetApi.getAvailability(form.department_id).then(setBudgetLines);
    } else {
      setBudgetLines([]);
    }
  }, [form.department_id]);

  const selectedBudgetLine = budgetLines.find(l => l.id === form.budget_line_id);

  const handleSubmit = async () => {
    setError('');
    try {
      await purchaseOrdersApi.create(form);
      navigate('/orders');
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail || 'Hiba történt');
    }
  };

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto', maxWidth: '800px' }}>
      <button onClick={() => navigate('/orders')} style={{
        display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none',
        cursor: 'pointer', color: '#666', fontSize: '13px', marginBottom: '16px',
      }}>
        <ArrowLeft size={14} /> {t('common.back')}
      </button>

      <h1 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '20px' }}>Új megrendelés</h1>

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', marginBottom: '16px', color: '#991b1b', fontSize: '13px' }}>
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <Field label="Osztály">
          <select value={form.department_id} onChange={e => setForm({ ...form, department_id: e.target.value, budget_line_id: '' })} style={inputStyle}>
            <option value="">Válassz osztályt...</option>
            {departments.map(d => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
          </select>
        </Field>

        <Field label="Budget sor">
          <select value={form.budget_line_id} onChange={e => {
            const bl = budgetLines.find(l => l.id === e.target.value);
            setForm({ ...form, budget_line_id: e.target.value, accounting_code: bl?.account_code || form.accounting_code });
          }} style={inputStyle}>
            <option value="">Válassz budget sort...</option>
            {budgetLines.map(l => (
              <option key={l.id} value={l.id}>
                {l.account_code} - {l.account_name} ({l.period}) — Szabad: {formatCurrency(l.available || 0, l.currency)}
              </option>
            ))}
          </select>
          {selectedBudgetLine && (
            <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
              Tervezett: {formatCurrency(selectedBudgetLine.planned_amount)} | Lekötött: {formatCurrency(selectedBudgetLine.committed || 0)} | Szabad: <strong style={{ color: (selectedBudgetLine.available || 0) >= 0 ? '#10B981' : '#EF4444' }}>{formatCurrency(selectedBudgetLine.available || 0)}</strong>
            </div>
          )}
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          <Field label="Szállító neve">
            <input value={form.supplier_name} onChange={e => setForm({ ...form, supplier_name: e.target.value })} style={inputStyle} />
          </Field>
          <Field label="Szállító adószáma">
            <input value={form.supplier_tax_id} onChange={e => setForm({ ...form, supplier_tax_id: e.target.value })} style={inputStyle} placeholder="12345678-2-42" />
          </Field>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '14px' }}>
          <Field label="Összeg">
            <input type="number" value={form.amount || ''} onChange={e => setForm({ ...form, amount: Number(e.target.value) })} style={inputStyle} />
          </Field>
          <Field label="Deviza">
            <select value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} style={inputStyle}>
              <option value="HUF">HUF</option>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
            </select>
          </Field>
          <Field label="Számla kód">
            <input value={form.accounting_code} onChange={e => setForm({ ...form, accounting_code: e.target.value })} style={inputStyle} />
          </Field>
        </div>

        <Field label="Leírás">
          <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
            style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} />
        </Field>

        <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
          <button onClick={handleSubmit} style={{
            padding: '10px 20px', background: '#06B6D4', color: '#fff', border: 'none',
            borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 500,
          }}>
            Megrendelés létrehozása
          </button>
          <button onClick={() => navigate('/orders')} style={{
            padding: '10px 20px', background: '#fff', color: '#666', border: '1px solid #d1d5db',
            borderRadius: '6px', cursor: 'pointer', fontSize: '14px',
          }}>
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#555', marginBottom: '4px', textTransform: 'uppercase' }}>{label}</label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', outline: 'none', boxSizing: 'border-box' };
