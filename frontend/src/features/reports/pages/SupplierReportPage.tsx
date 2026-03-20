import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { reportsApi } from '../../../services/api/reports';
import { formatCurrency } from '../../../utils/formatters';

export function SupplierReportPage() {
  const { t } = useTranslation();
  const [suppliers, setSuppliers] = useState<any[]>([]);

  useEffect(() => { reportsApi.suppliers().then(setSuppliers); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '1000px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('reports.suppliers')}</h1>
      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666' }}>Name</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666' }}>Tax Number</th>
              <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#666' }}>Invoices</th>
              <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#666' }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.map((s: any) => (
              <tr key={s.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{s.name}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{s.tax_number || '-'}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', textAlign: 'right' }}>{s.invoice_count}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', textAlign: 'right' }}>{formatCurrency(s.total_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {suppliers.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
