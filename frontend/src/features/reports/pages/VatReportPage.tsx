import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { reportsApi } from '../../../services/api/reports';
import { formatCurrency } from '../../../utils/formatters';

export function VatReportPage() {
  const { t } = useTranslation();
  const [report, setReport] = useState<any>(null);

  useEffect(() => { reportsApi.vat().then(setReport); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('reports.vat')}</h1>
      {report && (
        <div style={{ background: '#fff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <p><strong>Year:</strong> {report.year}</p>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '16px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>VAT Rate</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Count</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Net</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>VAT</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Gross</th>
              </tr>
            </thead>
            <tbody>
              {(report.by_vat_rate || []).map((row: any) => (
                <tr key={row.rate} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '8px' }}>{row.rate}%</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{row.count}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(row.net)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(row.vat)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(row.gross)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
