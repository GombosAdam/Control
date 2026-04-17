import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { departmentsApi } from '../../../services/api/departments';
import { budgetApi } from '../../../services/api/budget';
import { partnersApi } from '../../../services/api/partners';
import { accountsApi } from '../../../services/api/accounts';
import { formatCurrency } from '../../../utils/formatters';
import { useAuthStore } from '../../../stores/authStore';
import type { Department, BudgetLine, AccountMaster } from '../../../types/controlling';
import type { Partner } from '../../../types/partner';

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
  const [partners, setPartners] = useState<Partner[]>([]);
  const [accounts, setAccounts] = useState<AccountMaster[]>([]);
  const [error, setError] = useState('');
  const [showPOs, setShowPOs] = useState(false);

  const canSelectAnyDepartment = user?.role === 'admin' || user?.role === 'cfo';

  const [form, setForm] = useState({
    department_id: '', budget_line_id: '',
    partner_id: '', supplier_name: '', supplier_tax_id: '',
    currency: 'HUF', accounting_code: '', description: '',
  });
  const [lines, setLines] = useState<LineItem[]>([
    { description: '', quantity: 1, unit_price: 0 },
  ]);

  useEffect(() => {
    departmentsApi.list().then((depts: Department[]) => {
      setDepartments(depts);
      if (!canSelectAnyDepartment && user?.department_id) {
        const userDept = depts.find(d => d.id === user.department_id);
        if (userDept) setForm(prev => ({ ...prev, department_id: userDept.id }));
      }
    });
    partnersApi.list({ partner_type: 'supplier', limit: 100 }).then(data => setPartners(data.items));
    accountsApi.list({ active: true }).then(setAccounts).catch(() => {});
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
  const addLine = () => setLines(prev => [...prev, { description: '', quantity: 1, unit_price: 0 }]);
  const removeLine = (idx: number) => { if (lines.length > 1) setLines(prev => prev.filter((_, i) => i !== idx)); };

  const handleSubmit = async () => {
    setError('');
    if (lines.some(l => !l.description.trim())) { setError('Minden tételsor leírása kötelező'); return; }
    if (lines.some(l => l.quantity <= 0 || l.unit_price <= 0)) { setError('Mennyiség és egységár pozitív kell legyen'); return; }
    try {
      await purchaseOrdersApi.create({ ...form, lines });
      navigate('/orders');
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.message || err.response?.data?.detail || 'Hiba történt');
    }
  };

  return (
    <div style={{ padding: '12px 20px', height: '100vh', overflow: 'auto', maxWidth: '1100px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <button onClick={() => navigate('/orders')} style={{
          display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none',
          cursor: 'pointer', color: '#666', fontSize: '13px',
        }}>
          <ArrowLeft size={14} /> {t('common.back')}
        </button>
        <h1 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>Új megrendelés</h1>
      </div>

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', marginBottom: '10px', color: '#991b1b', fontSize: '12px' }}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* Two column layout: left = form, right = budget info */}
      <div style={{ display: 'grid', gridTemplateColumns: budgetStatus ? '1fr 320px' : '1fr', gap: '16px' }}>

        {/* LEFT: Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Row 1: Dept + Budget line */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <Field label="Osztály">
              {canSelectAnyDepartment ? (
                <select value={form.department_id} onChange={e => setForm({ ...form, department_id: e.target.value, budget_line_id: '' })} style={inputStyle}>
                  <option value="">Válassz...</option>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
                </select>
              ) : (
                <div style={{ ...inputStyle, background: '#f3f4f6', color: '#374151' }}>
                  {departments.find(d => d.id === form.department_id)?.name || 'Nincs osztály'}
                </div>
              )}
            </Field>
            <Field label="Budget sor">
              <select value={form.budget_line_id} onChange={e => {
                const bl = budgetLines.find(l => l.id === e.target.value);
                setForm({ ...form, budget_line_id: e.target.value, accounting_code: bl?.account_code || form.accounting_code });
              }} style={inputStyle}>
                <option value="">Válassz...</option>
                {budgetLines.map(l => (
                  <option key={l.id} value={l.id}>
                    {l.account_code} - {l.account_name} ({l.period}) — {formatCurrency(l.available || 0, l.currency)}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {/* Row 2: Partner */}
          <Field label="Szállító partner">
            <select value={form.partner_id} onChange={e => {
              const p = partners.find(x => x.id === e.target.value);
              setForm({
                ...form, partner_id: e.target.value,
                supplier_name: p?.name || form.supplier_name,
                supplier_tax_id: p?.tax_number || form.supplier_tax_id,
                accounting_code: p?.default_accounting_code || form.accounting_code,
              });
            }} style={inputStyle}>
              <option value="">Válassz partnert vagy írj be kézzel...</option>
              {partners.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.tax_number ? `(${p.tax_number})` : ''} {p.city ? `— ${p.city}` : ''} {p.is_verified ? '✓' : ''}
                </option>
              ))}
            </select>
          </Field>

          {/* Row 3: Supplier details + currency + account */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 100px 1fr', gap: '8px' }}>
            <Field label="Szállító neve">
              <input value={form.supplier_name} onChange={e => setForm({ ...form, supplier_name: e.target.value })} style={inputStyle} />
            </Field>
            <Field label="Adószám">
              <input value={form.supplier_tax_id} onChange={e => setForm({ ...form, supplier_tax_id: e.target.value })} style={inputStyle} placeholder="12345678-2-42" />
            </Field>
            <Field label="Deviza">
              <select value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} style={inputStyle}>
                <option value="HUF">HUF</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </Field>
            <Field label="Számla kód">
              <select value={form.accounting_code} onChange={e => setForm({ ...form, accounting_code: e.target.value })} style={inputStyle}>
                <option value="">Válassz...</option>
                {accounts.filter(a => !a.is_header).map(a => (
                  <option key={a.code} value={a.code}>{a.code} — {a.name}</option>
                ))}
              </select>
            </Field>
          </div>

          {/* Line items — compact */}
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#555', marginBottom: '4px', textTransform: 'uppercase' }}>Tételsorok</label>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={thStyle}>#</th>
                  <th style={{ ...thStyle, textAlign: 'left' }}>Leírás</th>
                  <th style={thStyle}>Menny.</th>
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
                        style={{ ...inputStyle, width: '100%', padding: '5px 8px' }} placeholder="Tétel leírása" />
                    </td>
                    <td style={tdStyle}>
                      <input type="number" value={line.quantity || ''} onChange={e => updateLine(idx, 'quantity', Number(e.target.value))}
                        style={{ ...inputStyle, width: '70px', textAlign: 'right', padding: '5px 8px' }} min={0} />
                    </td>
                    <td style={tdStyle}>
                      <input type="number" value={line.unit_price || ''} onChange={e => updateLine(idx, 'unit_price', Number(e.target.value))}
                        style={{ ...inputStyle, width: '100px', textAlign: 'right', padding: '5px 8px' }} min={0} />
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>
                      {formatCurrency(line.quantity * line.unit_price, form.currency)}
                    </td>
                    <td style={tdStyle}>
                      {lines.length > 1 && (
                        <button onClick={() => removeLine(idx)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444', padding: '2px' }}>
                          <Trash2 size={12} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4} style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 600, fontSize: '13px' }}>Összesen:</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, fontSize: '13px' }}>
                    {formatCurrency(totalAmount, form.currency)}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
            <button onClick={addLine} style={{
              display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px', marginTop: '4px',
              background: '#f9fafb', border: '1px dashed #d1d5db', borderRadius: '4px',
              cursor: 'pointer', fontSize: '11px', color: '#666',
            }}>
              <Plus size={12} /> Sor hozzáadása
            </button>
          </div>

          {/* Description — single line or small */}
          <Field label="Megjegyzés">
            <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
              style={inputStyle} placeholder="Opcionális megjegyzés..." />
          </Field>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button onClick={handleSubmit} style={{
              padding: '8px 20px', background: '#06B6D4', color: '#fff', border: 'none',
              borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
            }}>
              Megrendelés létrehozása
            </button>
            <button onClick={() => navigate('/orders')} style={{
              padding: '8px 16px', background: '#fff', color: '#666', border: '1px solid #d1d5db',
              borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
            }}>
              {t('common.cancel')}
            </button>
          </div>
        </div>

        {/* RIGHT: Budget status panel */}
        {budgetStatus && (
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', alignSelf: 'flex-start', position: 'sticky', top: '12px' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: '10px' }}>Budget keret</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
              <KpiBox label="Tervezett" value={formatCurrency(budgetStatus.budget_line.planned_amount, budgetStatus.budget_line.currency)} color="#1e293b" />
              <KpiBox label="Lekötött" value={formatCurrency(budgetStatus.committed, budgetStatus.budget_line.currency)} color="#F59E0B" />
              <KpiBox label="Tényleges" value={formatCurrency(budgetStatus.actual, budgetStatus.budget_line.currency)} color="#6366F1" />
              <KpiBox label="Szabad" value={formatCurrency(budgetStatus.available, budgetStatus.budget_line.currency)} color={budgetStatus.available >= 0 ? '#10B981' : '#EF4444'} />
            </div>

            {totalAmount > 0 && (
              <div style={{
                padding: '6px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, textAlign: 'center', marginBottom: '8px',
                background: totalAmount <= budgetStatus.available ? '#d1fae5' : '#fef2f2',
                color: totalAmount <= budgetStatus.available ? '#065f46' : '#991b1b',
              }}>
                Megrendelés: {formatCurrency(totalAmount, form.currency)} → Marad: {formatCurrency(budgetStatus.available - totalAmount, budgetStatus.budget_line.currency)}
              </div>
            )}

            {budgetStatus.purchase_orders.length > 0 && (
              <div>
                <button onClick={() => setShowPOs(!showPOs)} style={{
                  display: 'flex', alignItems: 'center', gap: '4px', background: 'none', border: 'none',
                  cursor: 'pointer', fontSize: '10px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', padding: 0,
                }}>
                  {showPOs ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  Aktív PO-k ({budgetStatus.purchase_orders.length})
                </button>
                {showPOs && (
                  <div style={{ marginTop: '6px', maxHeight: '150px', overflow: 'auto' }}>
                    {budgetStatus.purchase_orders.map((po: any) => (
                      <div key={po.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: '11px', borderBottom: '1px solid #f1f5f9' }}>
                        <span style={{ color: '#06B6D4', fontWeight: 600 }}>{po.po_number}</span>
                        <span style={{ fontWeight: 500 }}>{formatCurrency(po.amount, po.currency)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#555', marginBottom: '2px', textTransform: 'uppercase' }}>{label}</label>
      {children}
    </div>
  );
}

function KpiBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '6px 4px', background: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
      <div style={{ fontSize: '9px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: '13px', fontWeight: 700, color, marginTop: '2px' }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: '5px', fontSize: '12px', outline: 'none', boxSizing: 'border-box' };
const thStyle: React.CSSProperties = { padding: '4px 6px', fontSize: '10px', color: '#888', fontWeight: 600, textTransform: 'uppercase', textAlign: 'right' };
const tdStyle: React.CSSProperties = { padding: '4px 6px' };
