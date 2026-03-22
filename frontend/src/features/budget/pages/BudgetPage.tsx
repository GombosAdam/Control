import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Lock, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import { budgetApi } from '../../../services/api/budget';
import { departmentsApi } from '../../../services/api/departments';
import { formatCurrency } from '../../../utils/formatters';
import type { BudgetLine, Department } from '../../../types/controlling';

const statusColors: Record<string, { bg: string; color: string }> = {
  draft: { bg: '#fef3c7', color: '#92400e' },
  approved: { bg: '#d1fae5', color: '#065f46' },
  locked: { bg: '#dbeafe', color: '#1e40af' },
};

const pnlColors: Record<string, { bg: string; color: string }> = {
  revenue: { bg: '#d1fae5', color: '#065f46' },
  cogs: { bg: '#fee2e2', color: '#991b1b' },
  opex: { bg: '#fef3c7', color: '#92400e' },
  depreciation: { bg: '#e0e7ff', color: '#1e40af' },
  interest: { bg: '#fef3c7', color: '#92400e' },
  tax: { bg: '#f1f5f9', color: '#475569' },
};

export function BudgetPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<BudgetLine[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [deptFilter, setDeptFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const load = () => {
    budgetApi.listLines({
      page, limit: 50,
      department_id: deptFilter || undefined,
      period: periodFilter || undefined,
      status: statusFilter || undefined,
    }).then(data => { setItems(data.items); setTotal(data.total); });
  };

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);
  useEffect(() => { load(); }, [page, deptFilter, periodFilter, statusFilter]);

  const handleApprove = async (id: string) => { await budgetApi.approveLine(id); load(); };
  const handleLock = async (id: string) => { await budgetApi.lockLine(id); load(); };

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>
          {t('nav.budget')} <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total})</span>
        </h1>
      </div>

      {/* Info banner */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px',
        background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', marginBottom: '16px',
        fontSize: '13px', color: '#1e40af',
      }}>
        <Info size={16} />
        <span>
          A terv sorok a{' '}
          <Link to="/controlling/ebitda" style={{ color: '#1e40af', fontWeight: 600, textDecoration: 'underline' }}>
            Controlling → P&L
          </Link>
          {' '}nézetben szerkeszthetők.
        </span>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={selectStyle}>
          <option value="">{t('nav.departments')} - {t('invoices.all')}</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <input type="month" value={periodFilter} onChange={e => setPeriodFilter(e.target.value)} style={inputStyle} />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={selectStyle}>
          <option value="">{t('invoices.status')} - {t('invoices.all')}</option>
          <option value="draft">Draft</option>
          <option value="approved">Approved</option>
          <option value="locked">Locked</option>
        </select>
      </div>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {['Osztály', 'Kód', 'Megnevezés', 'P&L', 'Időszak', 'Tervezett', 'Lekötött', 'Tény', 'Szabad', 'Státusz', 'Műveletek'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={tdStyle}>{item.department_name || '-'}</td>
              <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{item.account_code}</td>
              <td style={tdStyle}>{item.account_name}</td>
              <td style={tdStyle}>
                {item.pnl_category && (
                  <span style={{
                    padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                    ...(pnlColors[item.pnl_category] || { bg: '#f3f4f6', color: '#666' }),
                  }}>{item.pnl_category}</span>
                )}
              </td>
              <td style={tdStyle}>{item.period}</td>
              <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.planned_amount, item.currency)}</td>
              <td style={{ ...tdStyle, textAlign: 'right', color: '#F59E0B' }}>{item.committed != null ? formatCurrency(item.committed, item.currency) : '-'}</td>
              <td style={{ ...tdStyle, textAlign: 'right', color: '#3B82F6' }}>{item.actual != null ? formatCurrency(item.actual, item.currency) : '-'}</td>
              <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600, color: (item.available ?? 0) < 0 ? '#EF4444' : '#10B981' }}>
                {item.available != null ? formatCurrency(item.available, item.currency) : '-'}
              </td>
              <td style={tdStyle}>
                <span style={{
                  padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                  ...statusColors[item.status],
                }}>{item.status}</span>
              </td>
              <td style={tdStyle}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {item.status === 'draft' && (
                    <button onClick={() => handleApprove(item.id)} title="Approve" style={actionBtnStyle}>
                      <Check size={12} />
                    </button>
                  )}
                  {item.status === 'approved' && (
                    <button onClick={() => handleLock(item.id)} title="Lock" style={actionBtnStyle}>
                      <Lock size={12} />
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
    </div>
  );
}

const thStyle: React.CSSProperties = { padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' };
const tdStyle: React.CSSProperties = { padding: '8px 10px', whiteSpace: 'nowrap' };
const inputStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', outline: 'none' };
const selectStyle: React.CSSProperties = { ...inputStyle, background: '#fff' };
const actionBtnStyle: React.CSSProperties = { padding: '4px 8px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center' };
