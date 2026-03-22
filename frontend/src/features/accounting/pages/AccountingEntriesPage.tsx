import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { accountingApi } from '../../../services/api/accounting';
import { departmentsApi } from '../../../services/api/departments';
import { formatCurrency, formatDateTime } from '../../../utils/formatters';
import type { AccountingEntry, Department } from '../../../types/controlling';

export function AccountingEntriesPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<AccountingEntry[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [deptFilter, setDeptFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');

  const load = () => {
    accountingApi.listEntries({
      page, limit: 50,
      department_id: deptFilter || undefined,
      period: periodFilter || undefined,
    }).then((data: any) => { setItems(data.items); setTotal(data.total); });
  };

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);
  useEffect(() => { load(); }, [page, deptFilter, periodFilter]);

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <h1 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>
        Könyvelési tételek <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total})</span>
      </h1>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={selectStyle}>
          <option value="">Minden osztály</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <input type="month" value={periodFilter} onChange={e => setPeriodFilter(e.target.value)} style={inputStyle} />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {['Időszak', 'Osztály', 'Számla kód', 'PO szám', 'Összeg', 'Deviza', 'Típus', 'Könyvelte', 'Könyvelve'].map(h => (
              <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(entry => (
            <tr key={entry.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 10px' }}>{entry.period}</td>
              <td style={{ padding: '8px 10px' }}>{entry.department_name || '-'}</td>
              <td style={{ padding: '8px 10px', fontFamily: 'monospace' }}>{entry.account_code}</td>
              <td style={{ padding: '8px 10px', color: '#06B6D4', fontWeight: 500 }}>{entry.po_number || '-'}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(entry.amount, entry.currency)}</td>
              <td style={{ padding: '8px 10px' }}>
                <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600, background: '#dbeafe', color: '#1e40af' }}>
                  {entry.currency}
                </span>
              </td>
              <td style={{ padding: '8px 10px' }}>
                <span style={{
                  padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                  background: entry.entry_type === 'debit' ? '#fef3c7' : '#d1fae5',
                  color: entry.entry_type === 'debit' ? '#92400e' : '#065f46',
                }}>{entry.entry_type}</span>
              </td>
              <td style={{ padding: '8px 10px', color: '#666' }}>{entry.posted_by || '-'}</td>
              <td style={{ padding: '8px 10px', color: '#666', fontSize: '11px' }}>{formatDateTime(entry.posted_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
    </div>
  );
}

const selectStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', background: '#fff' };
const inputStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px' };
