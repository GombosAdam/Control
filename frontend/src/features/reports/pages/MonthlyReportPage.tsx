import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { reportsApi } from '../../../services/api/reports';
import { formatCurrency } from '../../../utils/formatters';

export function MonthlyReportPage() {
  const { t } = useTranslation();
  const [report, setReport] = useState<any>(null);

  useEffect(() => { reportsApi.monthly().then(setReport); }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px' }}>{t('reports.monthly')}</h1>
      {report && (
        <div style={{ background: '#fff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <p><strong>Period:</strong> {report.year}/{report.month}</p>
          <p><strong>Invoice count:</strong> {report.invoice_count}</p>
          <p><strong>Net:</strong> {formatCurrency(report.total_net)}</p>
          <p><strong>VAT:</strong> {formatCurrency(report.total_vat)}</p>
          <p><strong>Gross:</strong> {formatCurrency(report.total_gross)}</p>
        </div>
      )}
    </div>
  );
}
