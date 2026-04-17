import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { navApi, NavConfig, NavSyncLog } from '../../../services/api/nav';
import { RefreshCw, Play } from 'lucide-react';

const btnStyle: React.CSSProperties = {
  padding: '8px 16px', borderRadius: '6px', border: 'none',
  cursor: 'pointer', fontSize: '14px', fontWeight: 500,
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px', border: '1px solid #d1d5db',
  borderRadius: '6px', fontSize: '14px',
};

const statusColors: Record<string, { bg: string; color: string }> = {
  running: { bg: '#FEF3C7', color: '#D97706' },
  completed: { bg: '#D1FAE5', color: '#059669' },
  error: { bg: '#FEE2E2', color: '#DC2626' },
};

export function NavSyncPage() {
  const { t } = useTranslation();
  const [configs, setConfigs] = useState<NavConfig[]>([]);
  const [logs, setLogs] = useState<NavSyncLog[]>([]);
  const [selectedConfig, setSelectedConfig] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [syncing, setSyncing] = useState(false);

  const loadLogs = () => {
    navApi.listSyncLogs({ limit: 50 }).then(data => setLogs(data.items || []));
  };

  useEffect(() => {
    navApi.listConfigs({ limit: 50 }).then(data => {
      const items = data.items || [];
      setConfigs(items);
      if (items.length > 0) setSelectedConfig(items[0].id);
    });
    loadLogs();

    // Set default dates
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    setDateTo(today.toISOString().slice(0, 10));
    setDateFrom(weekAgo.toISOString().slice(0, 10));
  }, []);

  // Auto-refresh while any sync is running
  useEffect(() => {
    const hasRunning = logs.some(l => l.status === 'running');
    if (hasRunning) {
      const interval = setInterval(loadLogs, 5000);
      return () => clearInterval(interval);
    }
  }, [logs]);

  const handleStartSync = async () => {
    if (!selectedConfig || !dateFrom || !dateTo) return;
    setSyncing(true);
    try {
      await navApi.startSync({ config_id: selectedConfig, date_from: dateFrom, date_to: dateTo });
      loadLogs();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px' }}>{t('navSync.title')}</h1>

      <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>{t('navSync.startSync')}</h3>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '4px' }}>{t('navSync.config')}</label>
            <select style={inputStyle} value={selectedConfig} onChange={e => setSelectedConfig(e.target.value)}>
              {configs.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '4px' }}>{t('navSync.dateFrom')}</label>
            <input type="date" style={inputStyle} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '4px' }}>{t('navSync.dateTo')}</label>
            <input type="date" style={inputStyle} value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </div>
          <button onClick={handleStartSync} disabled={syncing}
            style={{ ...btnStyle, background: '#DC2626', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Play size={16} /> {syncing ? t('navSync.syncing') : t('navSync.start')}
          </button>
          <button onClick={loadLogs} style={{ ...btnStyle, background: '#e5e7eb', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} /> {t('common.refresh')}
          </button>
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '10px' }}>{t('navSync.status')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.dateRange')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.found')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.created')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.skipped')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.startedAt')}</th>
            <th style={{ padding: '10px' }}>{t('navSync.completedAt')}</th>
          </tr>
        </thead>
        <tbody>
          {logs.map(log => {
            const sc = statusColors[log.status] || { bg: '#f3f4f6', color: '#6b7280' };
            return (
              <tr key={log.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '10px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 500, background: sc.bg, color: sc.color }}>
                    {log.status}
                  </span>
                  {log.error_message && (
                    <div style={{ fontSize: '12px', color: '#dc2626', marginTop: '4px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      title={log.error_message}>{log.error_message}</div>
                  )}
                </td>
                <td style={{ padding: '10px', fontSize: '13px' }}>{log.date_from} → {log.date_to}</td>
                <td style={{ padding: '10px', fontWeight: 600 }}>{log.invoices_found}</td>
                <td style={{ padding: '10px', fontWeight: 600, color: '#059669' }}>{log.invoices_created}</td>
                <td style={{ padding: '10px', color: '#6b7280' }}>{log.invoices_skipped}</td>
                <td style={{ padding: '10px', fontSize: '13px', color: '#6b7280' }}>
                  {log.started_at ? new Date(log.started_at).toLocaleString('hu-HU') : '-'}
                </td>
                <td style={{ padding: '10px', fontSize: '13px', color: '#6b7280' }}>
                  {log.completed_at ? new Date(log.completed_at).toLocaleString('hu-HU') : '-'}
                </td>
              </tr>
            );
          })}
          {logs.length === 0 && (
            <tr><td colSpan={7} style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>{t('navSync.noLogs')}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
