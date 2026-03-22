import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../../services/api/admin';
import {
  Activity, Database, Server, HardDrive, Cpu, Clock,
  RefreshCw, Zap, AlertTriangle, CheckCircle2, XCircle,
  ArrowUpDown, FileText, Users, Building2, Wallet, ShoppingCart,
  BookOpen, BarChart3, Shield, Layers,
} from 'lucide-react';

interface SystemData {
  status: string;
  timestamp: string;
  python_version: string;
  system: string;
  database: {
    status: string;
    size_mb: number;
    active_connections: number;
    total_connections: number;
    tables: Record<string, number>;
    error?: string;
  };
  redis: {
    status: string;
    used_memory_mb: number;
    connected_clients: number;
    uptime_seconds: number;
    total_commands: number;
    pubsub_channels: number;
    celery_queues: Record<string, number>;
    error?: string;
  };
  services: Record<string, {
    status: string;
    response_ms?: number;
    version?: string;
  }>;
  invoice_pipeline: Record<string, number>;
}

const STATUS_ICON: Record<string, { color: string; bg: string }> = {
  healthy: { color: '#10B981', bg: '#ecfdf5' },
  error: { color: '#EF4444', bg: '#fef2f2' },
  unreachable: { color: '#EF4444', bg: '#fef2f2' },
  unknown: { color: '#9CA3AF', bg: '#f9fafb' },
};

function StatusDot({ status }: { status: string }) {
  const s = STATUS_ICON[status] || STATUS_ICON.unknown;
  return (
    <div style={{
      width: '10px', height: '10px', borderRadius: '50%', background: s.color, flexShrink: 0,
      boxShadow: status === 'healthy' ? `0 0 8px ${s.color}` : 'none',
    }} />
  );
}

function Card({ children, title, icon: Icon, status, span }: {
  children: React.ReactNode;
  title: string;
  icon: any;
  status?: string;
  span?: number;
}) {
  const s = STATUS_ICON[status || 'unknown'] || STATUS_ICON.unknown;
  return (
    <div style={{
      background: '#fff', borderRadius: '12px', border: '1px solid #e5e7eb',
      padding: '20px', gridColumn: span ? `span ${span}` : undefined,
      borderTop: `3px solid ${s.color}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px', background: s.bg,
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: s.color,
          }}>
            <Icon size={16} />
          </div>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#333' }}>{title}</h3>
        </div>
        {status && <StatusDot status={status} />}
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, unit, mono }: { label: string; value: string | number; unit?: string; mono?: boolean }) {
  return (
    <div style={{ padding: '6px 0' }}>
      <div style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px' }}>{label}</div>
      <div style={{
        fontSize: '18px', fontWeight: 700, color: '#1f2937', marginTop: '2px',
        fontFamily: mono ? "'JetBrains Mono', monospace" : 'inherit',
      }}>
        {value}{unit && <span style={{ fontSize: '12px', color: '#9CA3AF', fontWeight: 400, marginLeft: '4px' }}>{unit}</span>}
      </div>
    </div>
  );
}

function PipelineBar({ statuses }: { statuses: Record<string, number> }) {
  const stages = [
    { key: 'uploaded', label: 'Feltöltve', color: '#94A3B8' },
    { key: 'ocr_processing', label: 'OCR', color: '#F59E0B' },
    { key: 'extracting', label: 'Kinyerés', color: '#F97316' },
    { key: 'pending_review', label: 'Review', color: '#3B82F6' },
    { key: 'in_approval', label: 'Jóváhagyás', color: '#8B5CF6' },
    { key: 'awaiting_match', label: 'PO-ra vár', color: '#06B6D4' },
    { key: 'matched', label: 'Párosítva', color: '#10B981' },
    { key: 'posted', label: 'Könyvelve', color: '#059669' },
    { key: 'rejected', label: 'Elutasítva', color: '#EF4444' },
    { key: 'error', label: 'Hiba', color: '#DC2626' },
  ];
  const total = Object.values(statuses).reduce((a, b) => a + b, 0);

  return (
    <div>
      {/* Stacked bar */}
      <div style={{ display: 'flex', height: '28px', borderRadius: '6px', overflow: 'hidden', marginBottom: '12px' }}>
        {stages.map(s => {
          const count = statuses[s.key] || 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={s.key}
              title={`${s.label}: ${count}`}
              style={{ width: `${pct}%`, background: s.color, minWidth: pct > 0 ? '3px' : 0, transition: 'width 300ms' }}
            />
          );
        })}
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px' }}>
        {stages.map(s => {
          const count = statuses[s.key] || 0;
          return (
            <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: s.color }} />
              <span style={{ color: '#666' }}>{s.label}</span>
              <span style={{ fontWeight: 600, color: '#333' }}>{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function QueueIndicator({ name, length }: { name: string; length: number }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '8px 12px', borderRadius: '8px',
      background: length > 0 ? '#fef3c7' : '#f9fafb',
      border: `1px solid ${length > 0 ? '#fcd34d' : '#e5e7eb'}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Layers size={14} color={length > 0 ? '#D97706' : '#9CA3AF'} />
        <span style={{ fontSize: '13px', fontWeight: 500 }}>{name}</span>
      </div>
      <span style={{
        fontSize: '14px', fontWeight: 700,
        color: length > 0 ? '#D97706' : '#10B981',
      }}>
        {length}
      </span>
    </div>
  );
}

const TABLE_ICONS: Record<string, any> = {
  invoices: FileText,
  users: Users,
  partners: Building2,
  budget_lines: Wallet,
  purchase_orders: ShoppingCart,
  accounting_entries: BookOpen,
  cfo_metrics: BarChart3,
  audit_logs: Shield,
  departments: Building2,
  scenarios: Layers,
};

export function SystemPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<SystemData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await adminApi.systemHealth();
      setData(result);
      setLastRefresh(new Date());
    } catch (e) {
      console.error('System health fetch failed', e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h ${m}m`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
            System Control Panel
          </h1>
          <p style={{ fontSize: '13px', color: '#999', margin: '4px 0 0' }}>
            Utolsó frissítés: {lastRefresh.toLocaleTimeString('hu-HU')}
            {data?.timestamp && ` — Server: ${new Date(data.timestamp).toLocaleTimeString('hu-HU')}`}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 20px', borderRadius: '8px', border: '1px solid #e5e7eb',
            background: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
            color: '#333', transition: 'all 150ms',
          }}
        >
          <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          Frissítés
        </button>
      </div>

      {!data ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>Betöltés...</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>

          {/* ── Services ── */}
          {Object.entries(data.services).map(([name, svc]) => (
            <Card key={name} title={name} icon={Server} status={svc.status}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#999' }}>Válaszidő</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: '#333' }}>
                    {svc.response_ms != null ? `${svc.response_ms}ms` : '—'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '12px', color: '#999' }}>Verzió</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#333' }}>{svc.version || '—'}</div>
                </div>
                <div style={{
                  padding: '4px 12px', borderRadius: '20px', fontSize: '11px', fontWeight: 600,
                  textTransform: 'uppercase', letterSpacing: '0.5px',
                  background: svc.status === 'healthy' ? '#ecfdf5' : '#fef2f2',
                  color: svc.status === 'healthy' ? '#059669' : '#DC2626',
                }}>
                  {svc.status}
                </div>
              </div>
            </Card>
          ))}

          {/* ── PostgreSQL ── */}
          <Card title="PostgreSQL" icon={Database} status={data.database.status}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <Metric label="Méret" value={data.database.size_mb} unit="MB" />
              <Metric label="Aktív conn" value={data.database.active_connections} />
              <Metric label="Összes conn" value={data.database.total_connections} />
              <Metric label="Python" value={data.python_version} />
            </div>
          </Card>

          {/* ── Redis ── */}
          <Card title="Redis" icon={Zap} status={data.redis.status}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <Metric label="Memória" value={data.redis.used_memory_mb} unit="MB" />
              <Metric label="Kliensek" value={data.redis.connected_clients} />
              <Metric label="Uptime" value={formatUptime(data.redis.uptime_seconds)} />
              <Metric label="Parancsok" value={data.redis.total_commands.toLocaleString()} />
            </div>
          </Card>

          {/* ── Celery Queues ── */}
          <Card title="Celery Queues" icon={ArrowUpDown} status={data.redis.status}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.redis.celery_queues && Object.entries(data.redis.celery_queues).map(([q, len]) => (
                <QueueIndicator key={q} name={q} length={len} />
              ))}
              <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                PubSub csatornák: {data.redis.pubsub_channels}
              </div>
            </div>
          </Card>

          {/* ── Invoice Pipeline ── */}
          <Card title="Invoice Pipeline" icon={Activity} status="healthy" span={3}>
            <PipelineBar statuses={data.invoice_pipeline} />
          </Card>

          {/* ── Database Tables ── */}
          <Card title="Adatbázis táblák" icon={HardDrive} status={data.database.status} span={3}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
              {data.database.tables && Object.entries(data.database.tables).map(([tbl, count]) => {
                const TblIcon = TABLE_ICONS[tbl] || Database;
                return (
                  <div key={tbl} style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '10px 12px', borderRadius: '8px', background: '#f9fafb',
                    border: '1px solid #f3f4f6',
                  }}>
                    <TblIcon size={14} color="#6B7280" />
                    <div>
                      <div style={{ fontSize: '11px', color: '#999' }}>{tbl}</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#333' }}>
                        {typeof count === 'number' ? count.toLocaleString() : '?'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
