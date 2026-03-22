import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { controllingApi } from '../../../services/api/controlling';
import { departmentsApi } from '../../../services/api/departments';
import { formatCurrency } from '../../../utils/formatters';
import type { PlanVsActual, Department } from '../../../types/controlling';

export function PlanActualPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<PlanVsActual[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [deptFilter, setDeptFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);

  useEffect(() => {
    controllingApi.planVsActual({
      department_id: deptFilter || undefined,
      period: periodFilter || undefined,
    }).then(setItems);
  }, [deptFilter, periodFilter]);

  const totalPlanned = items.reduce((s, i) => s + i.planned, 0);
  const totalActual = items.reduce((s, i) => s + i.actual, 0);
  const totalVariance = items.reduce((s, i) => s + i.variance, 0);

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <h1 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>Terv vs. Tény</h1>

      {/* Summary */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <SummaryCard label="Tervezett" value={formatCurrency(totalPlanned)} color="#F97316" />
        <SummaryCard label="Tény" value={formatCurrency(totalActual)} color="#3B82F6" />
        <SummaryCard label="Eltérés" value={formatCurrency(totalVariance)} color={totalVariance >= 0 ? '#10B981' : '#EF4444'} />
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={selectStyle}>
          <option value="">Minden osztály</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <input type="month" value={periodFilter} onChange={e => setPeriodFilter(e.target.value)} style={inputStyle} />
      </div>

      {/* Chart-like bar visualization */}
      {items.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          {items.slice(0, 10).map(item => {
            const maxVal = Math.max(...items.map(i => Math.max(i.planned, i.actual)));
            const plannedWidth = maxVal > 0 ? (item.planned / maxVal * 100) : 0;
            const actualWidth = maxVal > 0 ? (item.actual / maxVal * 100) : 0;
            return (
              <div key={`${item.department_id}-${item.account_code}-${item.period}`} style={{ marginBottom: '8px' }}>
                <div style={{ fontSize: '11px', color: '#555', marginBottom: '2px' }}>
                  {item.department_name} / {item.account_code} ({item.period})
                </div>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ height: '8px', background: '#fed7aa', borderRadius: '4px', width: `${plannedWidth}%`, marginBottom: '2px' }} />
                    <div style={{ height: '8px', background: '#93c5fd', borderRadius: '4px', width: `${actualWidth}%` }} />
                  </div>
                  <span style={{ fontSize: '10px', color: item.variance >= 0 ? '#10B981' : '#EF4444', minWidth: '50px', textAlign: 'right', fontWeight: 600 }}>
                    {item.variance_pct > 0 ? '+' : ''}{item.variance_pct}%
                  </span>
                </div>
              </div>
            );
          })}
          <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '10px', color: '#888' }}>
            <span><span style={{ display: 'inline-block', width: '12px', height: '8px', background: '#fed7aa', borderRadius: '2px', marginRight: '4px' }}></span>Terv</span>
            <span><span style={{ display: 'inline-block', width: '12px', height: '8px', background: '#93c5fd', borderRadius: '2px', marginRight: '4px' }}></span>Tény</span>
          </div>
        </div>
      )}

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {['Osztály', 'Kód', 'Megnevezés', 'Időszak', 'Tervezett', 'Tény', 'Lekötött', 'Eltérés', 'Eltérés %'].map(h => (
              <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 10px' }}>{item.department_name}</td>
              <td style={{ padding: '8px 10px', fontFamily: 'monospace' }}>{item.account_code}</td>
              <td style={{ padding: '8px 10px' }}>{item.account_name}</td>
              <td style={{ padding: '8px 10px' }}>{item.period}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(item.planned, item.currency)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', color: '#3B82F6' }}>{formatCurrency(item.actual, item.currency)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', color: '#F59E0B' }}>{formatCurrency(item.committed, item.currency)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600, color: item.variance >= 0 ? '#10B981' : '#EF4444' }}>
                {formatCurrency(item.variance, item.currency)}
              </td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600, color: item.variance_pct >= 0 ? '#10B981' : '#EF4444' }}>
                {item.variance_pct > 0 ? '+' : ''}{item.variance_pct}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: '12px 18px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', borderLeft: `3px solid ${color}`, minWidth: '160px' }}>
      <p style={{ margin: 0, fontSize: '10px', color: '#888', textTransform: 'uppercase' }}>{label}</p>
      <p style={{ margin: '4px 0 0', fontSize: '16px', fontWeight: 700, color: '#1a1a1a' }}>{value}</p>
    </div>
  );
}

const selectStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', background: '#fff' };
const inputStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px' };
