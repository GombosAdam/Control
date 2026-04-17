import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { departmentsApi } from '../../../services/api/departments';
import { budgetApi } from '../../../services/api/budget';
import { formatCurrency } from '../../../utils/formatters';
import { useAuthStore } from '../../../stores/authStore';
import type { Department, BudgetLine } from '../../../types/controlling';

interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
}

export function NewOrderPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [budgetLines, setBudgetLines] = useState<BudgetLine[]>([]);
  const [error, setError] = useState('');

  // Non-admin/cfo users can only order for their own department
  const canSelectAnyDepartment = user?.role === 'admin' || user?.role === 'cfo';

  const [form, setForm] = useState({
    department_id: '', budget_line_id: '',
    supplier_name: '', supplier_tax_id: '',
    currency: 'HUF', accounting_code: '', description: '',
  });
  const [lines, setLines] = useState<LineItem[]>([
    { description: '', quantity: 1, unit_price: 0 },
  ]);

  useEffect(() => {
    departmentsApi.list().then((depts: Department[]) => {
      setDepartments(depts);
      // Auto-select department for restricted users
      if (!canSelectAnyDepartment && user?.department_id) {
        const userDept = depts.find(d => d.id === user.department_id);
        if (userDept) {
          setForm(prev => ({ ...prev, department_id: userDept.id }));
        }
      }
    });
  }, []);

  useEffect(() => {
    if (form.department_id) {
      budgetApi.getAvailability(form.department_id).then(setBudgetLines);
    } else {
      setBudgetLines([]);
    }
  }, [form.department_id]);

  const [budgetStatus, setBudgetStatus] = useState<any>(null);

  useEffect(() => {
    if (form.budget_line_id) {
      budgetApi.getLineBudgetStatus(form.budget_line_id).then(setBudgetStatus).catch(() => setBudgetStatus(null));
    } else {
      setBudgetStatus(null);
    }
  }, [form.budget_line_id]);

  const selectedBudgetLine = budgetLines.find(l => l.id === form.budget_line_id);

  const totalAmount = lines.reduce((sum, l) => sum + l.quantity * l.unit_price, 0);

  const updateLine = (idx: number, field: keyof LineItem, value: string | number) => {
    setLines(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l));
  };

  const addLine = () => {
    setLines(prev => [...prev, { description: '', quantity: 1, unit_price: 0 }]);
  };

  const removeLine = (idx: number) => {
    if (lines.length <= 1) return;
    setLines(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async () => {
    setError('');
    if (lines.some(l => !l.description.trim())) {
      setError('Minden tételsor leírása kötelező');
      return;
    }
    if (lines.some(l => l.quantity <= 0 || l.unit_price <= 0)) {
      setError('Mennyiség és egységár pozitív kell legyen');
      return;
    }
    try {
      await purchaseOrdersApi.create({ ...form, lines });
      navigate('/orders');
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.message || err.response?.data?.detail || 'Hiba történt');
    }
  };

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto', maxWidth: '900px' }}>
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
          {canSelectAnyDepartment ? (
            <select value={form.department_id} onChange={e => setForm({ ...form, department_id: e.target.value, budget_line_id: '' })} style={inputStyle}>
              <option value="">Válassz osztályt...</option>
              {departments.map(d => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
            </select>
          ) : (
            <div style={{ ...inputStyle, background: '#f3f4f6', color: '#374151' }}>
              {departments.find(d => d.id === form.department_id)?.name || 'Nincs osztály hozzárendelve'}
            </div>
          )}
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

        {/* Budget keret és folyamatban lévő PO-k */}
        {budgetStatus && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '14px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px', marginBottom: '10px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Tervezett</div>
                <div style={{ fontSize: '16px', fontWeight: 700 }}>{formatCurrency(budgetStatus.budget_line.planned_amount, budgetStatus.budget_line.currency)}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Lekötött (PO)</div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: '#F59E0B' }}>{formatCurrency(budgetStatus.committed, budgetStatus.budget_line.currency)}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Tényleges</div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: '#6366F1' }}>{formatCurrency(budgetStatus.actual, budgetStatus.budget_line.currency)}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Szabad keret</div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: budgetStatus.available >= 0 ? '#10B981' : '#EF4444' }}>{formatCurrency(budgetStatus.available, budgetStatus.budget_line.currency)}</div>
              </div>
            </div>
            {totalAmount > 0 && (
              <div style={{ padding: '8px 12px', background: totalAmount <= budgetStatus.available ? '#d1fae5' : '#fef2f2', borderRadius: '6px', fontSize: '12px', fontWeight: 600, textAlign: 'center', color: totalAmount <= budgetStatus.available ? '#065f46' : '#991b1b' }}>
                Ez a megrendelés: {formatCurrency(totalAmount, form.currency)} → Maradék keret: {formatCurrency(budgetStatus.available - totalAmount, budgetStatus.budget_line.currency)}
              </div>
            )}
            {budgetStatus.purchase_orders.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#555', textTransform: 'uppercase', marginBottom: '6px' }}>Folyamatban lévő megrendelések ({budgetStatus.purchase_orders.length})</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #d1d5db' }}>
                      <th style={{ padding: '3px 6px', textAlign: 'left', color: '#888' }}>PO szám</th>
                      <th style={{ padding: '3px 6px', textAlign: 'left', color: '#888' }}>Szállító</th>
                      <th style={{ padding: '3px 6px', textAlign: 'left', color: '#888' }}>Státusz</th>
                      <th style={{ padding: '3px 6px', textAlign: 'right', color: '#888' }}>Összeg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {budgetStatus.purchase_orders.map((po: any) => (
                      <tr key={po.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={{ padding: '3px 6px', color: '#06B6D4', fontWeight: 600 }}>{po.po_number}</td>
                        <td style={{ padding: '3px 6px' }}>{po.supplier_name}</td>
                        <td style={{ padding: '3px 6px' }}>
                          <span style={{ padding: '1px 5px', borderRadius: '4px', fontSize: '10px', fontWeight: 600, background: po.status === 'approved' ? '#d1fae5' : '#fef3c7', color: po.status === 'approved' ? '#065f46' : '#92400e' }}>{po.status}</span>
                        </td>
                        <td style={{ padding: '3px 6px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(po.amount, po.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          <Field label="Szállító neve">
            <input value={form.supplier_name} onChange={e => setForm({ ...form, supplier_name: e.target.value })} style={inputStyle} />
          </Field>
          <Field label="Szállító adószáma">
            <input value={form.supplier_tax_id} onChange={e => setForm({ ...form, supplier_tax_id: e.target.value })} style={inputStyle} placeholder="12345678-2-42" />
          </Field>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
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

        {/* Line items */}
        <div>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#555', marginBottom: '8px', textTransform: 'uppercase' }}>Tételsorok</label>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={thStyle}>#</th>
                <th style={{ ...thStyle, textAlign: 'left' }}>Leírás</th>
                <th style={thStyle}>Mennyiség</th>
                <th style={thStyle}>Egységár</th>
                <th style={thStyle}>Nettó</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={tdStyle}>{idx + 1}</td>
                  <td style={tdStyle}>
                    <input value={line.description} onChange={e => updateLine(idx, 'description', e.target.value)}
                      style={{ ...inputStyle, width: '100%' }} placeholder="Tétel leírása" />
                  </td>
                  <td style={tdStyle}>
                    <input type="number" value={line.quantity || ''} onChange={e => updateLine(idx, 'quantity', Number(e.target.value))}
                      style={{ ...inputStyle, width: '80px', textAlign: 'right' }} min={0} />
                  </td>
                  <td style={tdStyle}>
                    <input type="number" value={line.unit_price || ''} onChange={e => updateLine(idx, 'unit_price', Number(e.target.value))}
                      style={{ ...inputStyle, width: '120px', textAlign: 'right' }} min={0} />
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>
                    {formatCurrency(line.quantity * line.unit_price, form.currency)}
                  </td>
                  <td style={tdStyle}>
                    {lines.length > 1 && (
                      <button onClick={() => removeLine(idx)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444', padding: '4px' }}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4} style={{ padding: '8px', textAlign: 'right', fontWeight: 600, fontSize: '14px' }}>Összesen:</td>
                <td style={{ padding: '8px', textAlign: 'right', fontWeight: 700, fontSize: '14px' }}>
                  {formatCurrency(totalAmount, form.currency)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
          <button onClick={addLine} style={{
            display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 12px', marginTop: '8px',
            background: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '6px',
            cursor: 'pointer', fontSize: '12px', color: '#666',
          }}>
            <Plus size={14} /> Sor hozzáadása
          </button>
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
const thStyle: React.CSSProperties = { padding: '6px 8px', fontSize: '11px', color: '#888', fontWeight: 600, textTransform: 'uppercase', textAlign: 'right' };
const tdStyle: React.CSSProperties = { padding: '6px 8px' };
