import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { TrendingUp, Receipt, Truck } from 'lucide-react';

export function ReportsPage() {
  const { t } = useTranslation();
  const cards = [
    { icon: TrendingUp, title: t('reports.monthly'), path: '/reports/monthly', color: '#1e3a5f' },
    { icon: Receipt, title: t('reports.vat'), path: '/reports/vat', color: '#2563eb' },
    { icon: Truck, title: t('reports.suppliers'), path: '/reports/suppliers', color: '#3b82f6' },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>
        {t('reports.title')}
      </h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {cards.map(card => (
          <Link key={card.path} to={card.path} style={{
            background: '#fff', borderRadius: '8px', padding: '32px', textAlign: 'center',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textDecoration: 'none', color: '#333',
            borderTop: `4px solid ${card.color}`,
          }}>
            <card.icon size={40} color={card.color} style={{ marginBottom: '12px' }} />
            <p style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>{card.title}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
