import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { controllingApi } from '../../../services/api/controlling';
import { departmentsApi } from '../../../services/api/departments';
import { formatCurrency } from '../../../utils/formatters';
import type { CommitmentReport, Department } from '../../../types/controlling';

const statusColors: Record<string, { bg: string; color: string }> = {
  approved: { bg: '#d1fae5', color: '#065f46' },
  received: { bg: '#dbeafe', color: '#1e40af' },
};

export function CommitmentPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<CommitmentReport[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [deptFilter, setDeptFilter] = useState('');

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);

  useEffect(() => {
    controllingApi.commitment({
      department_id: deptFilter || undefined,
    }).then(setItems);
  }, [deptFilter]);

  const totalCommitment = items.reduce((s, i) => s + i.amount, 0);

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <h1 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>Lekötések (Open Commitments)</h1>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'center' }}>
        <div style={{ padding: '12px 18px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', borderLeft: '3px solid #06B6D4' }}>
          <p style={{ margin: 0, fontSize: '10px', color: '#888', textTransform: 'uppercase' }}>Összes lekötés</p>
          <p style={{ margin: '4px 0 0', fontSize: '16px', fontWeight: 700 }}>{formatCurrency(totalCommitment)}</p>
        </div>
        <div style={{ padding: '12px 18px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px', borderLeft: '3px solid #F59E0B' }}>
          <p style={{ margin: 0, fontSize: '10px', color: '#888', textTransform: 'uppercase' }}>Nyitott PO-k</p>
          <p style={{ margin: '4px 0 0', fontSize: '16px', fontWeight: 700 }}>{items.length} db</p>
        </div>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={{
          padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', background: '#fff', marginLeft: 'auto',
        }}>
          <option value="">Minden osztály</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {['PO szám', 'Osztály', 'Szállító', 'Összeg', 'Számla kód', 'Státusz', 'Létrehozva'].map(h => (
              <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(po => (
            <tr key={po.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 10px', fontWeight: 600, color: '#06B6D4' }}>{po.po_number}</td>
              <td style={{ padding: '8px 10px' }}>{po.department_name}</td>
              <td style={{ padding: '8px 10px' }}>{po.partner_name || po.supplier_name}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(po.amount, po.currency)}</td>
              <td style={{ padding: '8px 10px', fontFamily: 'monospace' }}>{po.accounting_code}</td>
              <td style={{ padding: '8px 10px' }}>
                <span style={{
                  padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                  ...(statusColors[po.status] || { bg: '#f3f4f6', color: '#374151' }),
                }}>{po.status}</span>
              </td>
              <td style={{ padding: '8px 10px', color: '#666', fontSize: '11px' }}>{new Date(po.created_at).toLocaleDateString('hu')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
    </div>
  );
}
