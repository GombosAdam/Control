import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, CheckCircle, Clock, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  BarChart, Bar,
} from 'recharts';
import { dashboardApi } from '../../../services/api/dashboard';
import { scenariosApi } from '../../../services/api/scenarios';
import { formatCurrency, formatDateTime } from '../../../utils/formatters';
import type { DashboardStats, CfoKpis, TrendDataPoint, DepartmentComparison, BudgetAlert } from '../../../types/report';
import type { Scenario } from '../../../types/controlling';

export function DashboardPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'invoices' | 'cfo'>('invoices');

  // Invoice tab state
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [processing, setProcessing] = useState<Record<string, number>>({});

  // CFO tab state
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState('');
  const [planType, setPlanType] = useState<'budget' | 'forecast'>('budget');
  const [kpis, setKpis] = useState<CfoKpis | null>(null);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [departments, setDepartments] = useState<DepartmentComparison[]>([]);
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);

  useEffect(() => {
    dashboardApi.getStats().then(setStats);
    dashboardApi.getRecent(10).then(setRecent);
    dashboardApi.getProcessingStatus().then(setProcessing);
    scenariosApi.list().then((list: Scenario[]) => {
      setScenarios(list);
      const def = list.find(s => s.is_default);
      if (def) setScenarioId(def.id);
      else if (list.length > 0) setScenarioId(list[0].id);
    });
  }, []);

  // Load CFO data when tab/filters change
  useEffect(() => {
    if (activeTab !== 'cfo') return;
    const params = { scenario_id: scenarioId || undefined, plan_type: planType };
    dashboardApi.getCfoKpis(params).then(setKpis);
    dashboardApi.getCfoTrends(params).then(setTrends);
    dashboardApi.getCfoDepartments(params).then(setDepartments);
    dashboardApi.getCfoAlerts({ ...params, threshold_pct: 10 }).then(setAlerts);
  }, [activeTab, scenarioId, planType]);

  const kpiCards = [
    { label: t('dashboard.totalInvoices'), value: stats?.total_invoices ?? 0, icon: FileText, color: '#3B82F6' },
    { label: t('dashboard.approved'), value: stats?.approved ?? 0, icon: CheckCircle, color: '#10B981' },
    { label: t('dashboard.pendingReview'), value: stats?.pending_review ?? 0, icon: Clock, color: '#F59E0B' },
    { label: t('dashboard.errors'), value: stats?.errors ?? 0, icon: AlertCircle, color: '#EF4444' },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '16px', color: '#1a1a1a' }}>
        {t('dashboard.title')}
      </h1>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '0', marginBottom: '24px', borderBottom: '2px solid #e5e7eb' }}>
        {[
          { key: 'invoices' as const, label: 'Számlák' },
          { key: 'cfo' as const, label: 'CFO' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 24px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: '14px', fontWeight: 600,
              color: activeTab === tab.key ? '#1d4ed8' : '#888',
              borderBottom: activeTab === tab.key ? '2px solid #1d4ed8' : '2px solid transparent',
              marginBottom: '-2px',
              transition: 'all 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ═══ INVOICES TAB ═══ */}
      {activeTab === 'invoices' && (
        <>
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
            borderLeft: '4px solid #1e3a5f',
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
        </>
      )}

      {/* ═══ CFO TAB ═══ */}
      {activeTab === 'cfo' && (
        <>
          {/* CFO Toolbar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px',
            background: '#fff', padding: '12px 20px', borderRadius: '10px',
            border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <select value={scenarioId} onChange={e => setScenarioId(e.target.value)}
              style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '13px', background: '#fff', outline: 'none' }}>
              {scenarios.map(s => (
                <option key={s.id} value={s.id}>{s.name}{s.is_default ? ' (alap)' : ''}</option>
              ))}
            </select>

            <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '3px' }}>
              {(['budget', 'forecast'] as const).map(pt => (
                <button
                  key={pt}
                  onClick={() => setPlanType(pt)}
                  style={{
                    padding: '6px 16px', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                    background: planType === pt ? '#fff' : 'transparent',
                    color: planType === pt ? (pt === 'budget' ? '#1d4ed8' : '#7c3aed') : '#888',
                    cursor: 'pointer',
                    boxShadow: planType === pt ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  }}
                >
                  {pt === 'budget' ? 'Budget' : 'Forecast'}
                </button>
              ))}
            </div>
          </div>

          {/* KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
            {kpis && (
              <>
                <CfoKpiCard label="Revenue" current={kpis.revenue.current} previous={kpis.revenue.previous} trendPct={kpis.revenue.trend_pct} color="#22c55e" />
                <CfoKpiCard label="EBITDA" current={kpis.ebitda.current} previous={kpis.ebitda.previous} trendPct={kpis.ebitda.trend_pct} color="#3b82f6" />
                <CfoKpiCard label="Net Income" current={kpis.net_income.current} previous={kpis.net_income.previous} trendPct={kpis.net_income.trend_pct} color="#8b5cf6" />
              </>
            )}
          </div>

          {/* Charts row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
            {/* Trend chart */}
            <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e5e7eb', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#333', marginBottom: '16px', margin: '0 0 16px' }}>Havi trend — Terv vs Tény</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={trends}>
                  <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${(v / 1000000).toFixed(1)}M`} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line type="monotone" dataKey="revenue_plan" name="Bevétel (terv)" stroke="#22c55e" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="revenue_actual" name="Bevétel (tény)" stroke="#22c55e" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                  <Line type="monotone" dataKey="ebitda_plan" name="EBITDA (terv)" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ebitda_actual" name="EBITDA (tény)" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Department comparison */}
            <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e5e7eb', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#333', marginBottom: '16px', margin: '0 0 16px' }}>Osztályok — Terv vs Tény</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={departments}>
                  <XAxis dataKey="department_name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${(v / 1000000).toFixed(1)}M`} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="planned" name="Terv" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="actual" name="Tény" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Alert table */}
          <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e5e7eb', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#333', margin: '0 0 16px' }}>
              <AlertCircle size={16} style={{ verticalAlign: 'middle', marginRight: '6px', color: '#ef4444' }} />
              Költségvetési figyelmeztetések
            </h3>
            {alerts.length === 0 ? (
              <p style={{ color: '#999', fontSize: '13px', textAlign: 'center', padding: '24px 0' }}>Nincsenek figyelmeztetések</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                    {['Számla', 'Osztály', 'Időszak', 'Terv', 'Tény', 'Túllépés %'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#6b7280', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((alert, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '8px 12px', color: '#333' }}>{alert.account_name}</td>
                      <td style={{ padding: '8px 12px', color: '#666' }}>{alert.department_name || '—'}</td>
                      <td style={{ padding: '8px 12px', color: '#666' }}>{alert.period}</td>
                      <td style={{ padding: '8px 12px', color: '#333', fontVariantNumeric: 'tabular-nums' }}>{formatCurrency(alert.planned)}</td>
                      <td style={{ padding: '8px 12px', color: '#dc2626', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{formatCurrency(alert.actual)}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{
                          background: alert.overage_pct >= 20 ? '#fee2e2' : '#fef3c7',
                          color: alert.overage_pct >= 20 ? '#dc2626' : '#d97706',
                          padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                        }}>
                          +{alert.overage_pct}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* CFO KPI Card */
function CfoKpiCard({ label, current, previous, trendPct, color }: {
  label: string; current: number; previous: number; trendPct: number; color: string;
}) {
  const isPositive = trendPct >= 0;
  return (
    <div style={{
      background: '#fff', borderRadius: '10px', padding: '20px',
      border: '1px solid #e5e7eb', borderTop: `3px solid ${color}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>{label}</span>
        {isPositive ? <TrendingUp size={16} color={color} /> : <TrendingDown size={16} color="#dc2626" />}
      </div>
      <div style={{ fontSize: '24px', fontWeight: 800, color: '#111', fontVariantNumeric: 'tabular-nums', marginBottom: '6px' }}>
        {formatCurrency(current)}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', color: '#999' }}>Előző: {formatCurrency(previous)}</span>
        <span style={{
          fontSize: '11px', fontWeight: 700,
          color: isPositive ? '#16a34a' : '#dc2626',
          background: isPositive ? '#f0fdf4' : '#fef2f2',
          padding: '2px 8px', borderRadius: '10px',
        }}>
          {isPositive ? '+' : ''}{trendPct}%
        </span>
      </div>
    </div>
  );
}
