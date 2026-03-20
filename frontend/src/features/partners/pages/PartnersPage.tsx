import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Plus } from 'lucide-react';
import { partnersApi } from '../../../services/api/partners';
import { formatCurrency } from '../../../utils/formatters';
import type { Partner } from '../../../types/partner';

export function PartnersPage() {
  const { t } = useTranslation();
  const [partners, setPartners] = useState<Partner[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    partnersApi.list({ search: search || undefined }).then(data => setPartners(data.items));
  }, []);

  const doSearch = () => {
    partnersApi.list({ search: search || undefined }).then(data => setPartners(data.items));
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#1a1a1a', margin: 0 }}>{t('partners.title')}</h1>
        <button style={{
          display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px',
          background: '#F59E0B', color: '#fff', border: 'none', borderRadius: '8px',
          fontSize: '14px', fontWeight: 500, cursor: 'pointer',
        }}>
          <Plus size={16} /> {t('partners.addPartner')}
        </button>
      </div>

      <div style={{ position: 'relative', marginBottom: '16px' }}>
        <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
        <input
          type="text" placeholder={t('common.search')} value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          style={{
            width: '100%', padding: '10px 12px 10px 36px', border: '1px solid #d1d5db',
            borderRadius: '8px', fontSize: '14px', outline: 'none', boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              {[t('partners.name'), t('partners.taxNumber'), t('partners.type'), t('partners.invoiceCount'), t('partners.totalAmount')].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {partners.map(p => (
              <tr key={p.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: 500 }}>{p.name}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px', color: '#666' }}>{p.tax_number || '-'}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500,
                    background: p.partner_type === 'supplier' ? '#fef3c7' : p.partner_type === 'customer' ? '#dbeafe' : '#e0e7ff',
                    color: p.partner_type === 'supplier' ? '#92400e' : p.partner_type === 'customer' ? '#1e40af' : '#4338ca',
                  }}>
                    {p.partner_type}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{p.invoice_count}</td>
                <td style={{ padding: '12px 16px', fontSize: '14px' }}>{formatCurrency(p.total_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {partners.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
