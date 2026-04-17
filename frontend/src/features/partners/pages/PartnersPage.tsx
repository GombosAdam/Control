import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Plus, CheckCircle, MapPin, Phone } from 'lucide-react';
import { partnersApi } from '../../../services/api/partners';
import { formatCurrency } from '../../../utils/formatters';
import type { Partner } from '../../../types/partner';

export function PartnersPage() {
  const { t } = useTranslation();
  const [partners, setPartners] = useState<Partner[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Partner | null>(null);

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

      <div style={{ display: 'flex', gap: '20px' }}>
        <div style={{ flex: 1, background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                {[t('partners.name'), t('partners.taxNumber'), 'Város', t('partners.type'), 'Fiz.hat.', t('partners.invoiceCount'), t('partners.totalAmount')].map(h => (
                  <th key={h} style={{ padding: '12px 12px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#666', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {partners.map(p => (
                <tr key={p.id} onClick={() => setSelected(p)} style={{
                  borderBottom: '1px solid #f3f4f6', cursor: 'pointer',
                  background: selected?.id === p.id ? '#f0f9ff' : 'transparent',
                }}>
                  <td style={{ padding: '10px 12px', fontSize: '13px', fontWeight: 500 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {p.name}
                      {p.is_verified && <CheckCircle size={13} color="#10B981" />}
                    </div>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '13px', color: '#666', fontFamily: 'monospace' }}>{p.tax_number || '-'}</td>
                  <td style={{ padding: '10px 12px', fontSize: '13px', color: '#666' }}>{p.city || '-'}</td>
                  <td style={{ padding: '10px 12px', fontSize: '13px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '12px', fontSize: '10px', fontWeight: 500,
                      background: p.partner_type === 'supplier' ? '#fef3c7' : p.partner_type === 'customer' ? '#dbeafe' : '#e0e7ff',
                      color: p.partner_type === 'supplier' ? '#92400e' : p.partner_type === 'customer' ? '#1e40af' : '#4338ca',
                    }}>
                      {p.partner_type}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '13px', color: '#666' }}>{p.payment_terms_days} nap</td>
                  <td style={{ padding: '10px 12px', fontSize: '13px' }}>{p.invoice_count}</td>
                  <td style={{ padding: '10px 12px', fontSize: '13px' }}>{formatCurrency(p.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {partners.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
          )}
        </div>

        {/* Partner detail panel */}
        {selected && (
          <div style={{ width: '340px', background: '#fff', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', alignSelf: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>{selected.name}</h2>
              {selected.is_verified && (
                <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '10px', fontWeight: 600, background: '#d1fae5', color: '#065f46' }}>NAV Verified</span>
              )}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
              <DetailRow label="Adószám" value={selected.tax_number} mono />
              <DetailRow label="Típus" value={selected.partner_type} />
              {selected.city && (
                <DetailRow label="Cím" value={`${selected.zip_code || ''} ${selected.city}`} icon={<MapPin size={13} />} />
              )}
              {selected.address && <DetailRow label="Teljes cím" value={selected.address} />}
              {selected.contact_person && <DetailRow label="Kapcsolattartó" value={selected.contact_person} />}
              {selected.contact_phone && <DetailRow label="Telefon" value={selected.contact_phone} icon={<Phone size={13} />} />}
              {selected.contact_email && <DetailRow label="Email" value={selected.contact_email} />}
              <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '4px 0' }} />
              <DetailRow label="Fizetési határidő" value={`${selected.payment_terms_days} nap`} />
              <DetailRow label="Fizetési mód" value={selected.payment_method} />
              <DetailRow label="Pénznem" value={selected.currency} />
              {selected.iban && <DetailRow label="IBAN" value={selected.iban} mono />}
              {selected.swift_code && <DetailRow label="SWIFT" value={selected.swift_code} mono />}
              {selected.bank_account && <DetailRow label="Bankszámla" value={selected.bank_account} mono />}
              <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '4px 0' }} />
              <DetailRow label="Számlák" value={String(selected.invoice_count)} />
              <DetailRow label="Összforgalom" value={formatCurrency(selected.total_amount)} />
              {selected.default_accounting_code && <DetailRow label="Alapértelmezett számla" value={selected.default_accounting_code} mono />}
              {selected.notes && (
                <div style={{ marginTop: '4px', padding: '8px', background: '#f9fafb', borderRadius: '6px', fontSize: '12px', color: '#666' }}>
                  {selected.notes}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value, mono, icon }: { label: string; value: string | null; mono?: boolean; icon?: React.ReactNode }) {
  if (!value) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ color: '#666', display: 'flex', alignItems: 'center', gap: '4px' }}>{icon}{label}</span>
      <span style={{ fontWeight: 500, fontFamily: mono ? 'monospace' : 'inherit', fontSize: mono ? '12px' : '13px' }}>{value}</span>
    </div>
  );
}
