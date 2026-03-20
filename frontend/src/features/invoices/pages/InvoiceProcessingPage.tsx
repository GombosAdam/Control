import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { invoicesApi } from '../../../services/api/invoices';
import { formatDateTime } from '../../../utils/formatters';
import type { Invoice } from '../../../types/invoice';

export function InvoiceProcessingPage() {
  const { t } = useTranslation();
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    const load = () => {
      invoicesApi.list({ status: 'ocr_processing', limit: 50 }).then(data => setInvoices(data.items));
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>
        {t('nav.processing')}
      </h1>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {invoices.map(inv => (
          <div key={inv.id} style={{
            background: '#fff', borderRadius: '8px', padding: '16px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <p style={{ fontWeight: 500, margin: 0 }}>{inv.original_filename}</p>
              <p style={{ fontSize: '12px', color: '#666', margin: '4px 0 0' }}>{formatDateTime(inv.created_at)}</p>
            </div>
            <span style={{
              padding: '4px 12px', borderRadius: '12px', fontSize: '12px', fontWeight: 500,
              background: '#e0e7ff', color: '#4338ca',
            }}>
              {t(`status.${inv.status}`)}
            </span>
          </div>
        ))}
        {invoices.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
