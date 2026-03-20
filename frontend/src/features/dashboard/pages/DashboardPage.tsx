import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { dashboardApi } from '../../../services/api/dashboard';
import { formatCurrency, formatDateTime } from '../../../utils/formatters';
import type { DashboardStats } from '../../../types/report';

export function DashboardPage() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [processing, setProcessing] = useState<Record<string, number>>({});

  useEffect(() => {
    dashboardApi.getStats().then(setStats);
    dashboardApi.getRecent(10).then(setRecent);
    dashboardApi.getProcessingStatus().then(setProcessing);
  }, []);

  const kpiCards = [
    { label: t('dashboard.totalInvoices'), value: stats?.total_invoices ?? 0, icon: FileText, color: '#3B82F6' },
    { label: t('dashboard.approved'), value: stats?.approved ?? 0, icon: CheckCircle, color: '#10B981' },
    { label: t('dashboard.pendingReview'), value: stats?.pending_review ?? 0, icon: Clock, color: '#F59E0B' },
    { label: t('dashboard.errors'), value: stats?.errors ?? 0, icon: AlertCircle, color: '#EF4444' },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>
        {t('dashboard.title')}
      </h1>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        {kpiCards.map((card) => (
          <div key={card.label} style={{
            background: '#fff', borderRadius: '8px', padding: '20px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderLeft: `4px solid ${card.color}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>{card.label}</p>
                <p style={{ fontSize: '28px', fontWeight: 700, margin: '4px 0 0', color: '#1a1a1a' }}>{card.value}</p>
              </div>
              <card.icon size={32} color={card.color} strokeWidth={1.5} />
            </div>
          </div>
        ))}
      </div>

      {/* Total Amount */}
      <div style={{
        background: '#fff', borderRadius: '8px', padding: '20px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '32px',
        borderLeft: '4px solid #8B5CF6',
      }}>
        <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>{t('dashboard.totalAmount')}</p>
        <p style={{ fontSize: '28px', fontWeight: 700, margin: '4px 0 0', color: '#1a1a1a' }}>
          {formatCurrency(stats?.total_amount)}
        </p>
      </div>

      {/* Two columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Recent Invoices */}
        <div style={{ background: '#fff', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px' }}>{t('dashboard.recentInvoices')}</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {recent.map((inv: any) => (
              <div key={inv.id} style={{
                display: 'flex', justifyContent: 'space-between', padding: '8px 0',
                borderBottom: '1px solid #f3f4f6', fontSize: '13px',
              }}>
                <span style={{ color: '#333' }}>{inv.original_filename}</span>
                <span style={{
                  padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 500,
                  background: inv.status === 'approved' ? '#d1fae5' : inv.status === 'error' ? '#fee2e2' : '#e0e7ff',
                  color: inv.status === 'approved' ? '#059669' : inv.status === 'error' ? '#dc2626' : '#4338ca',
                }}>
                  {t(`status.${inv.status}`)}
                </span>
              </div>
            ))}
            {recent.length === 0 && (
              <p style={{ color: '#999', fontSize: '13px' }}>{t('common.noData')}</p>
            )}
          </div>
        </div>

        {/* Processing Status */}
        <div style={{ background: '#fff', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px' }}>{t('dashboard.processingStatus')}</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.entries(processing).map(([status, count]) => (
              <div key={status} style={{
                display: 'flex', justifyContent: 'space-between', padding: '8px 0',
                borderBottom: '1px solid #f3f4f6', fontSize: '13px',
              }}>
                <span>{t(`status.${status}`)}</span>
                <span style={{ fontWeight: 600 }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
