import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Target, BarChart3, GitCompareArrows } from 'lucide-react';
import { controllingApi } from '../../../services/api/controlling';
import { formatCurrency } from '../../../utils/formatters';
import type { BudgetStatusReport } from '../../../types/controlling';

export function ControllingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatusReport[]>([]);

  useEffect(() => {
    controllingApi.budgetStatus().then(setBudgetStatus);
  }, []);

  const totalPlanned = budgetStatus.reduce((s, d) => s + d.planned, 0);
  const totalCommitted = budgetStatus.reduce((s, d) => s + d.committed, 0);
  const totalSpent = budgetStatus.reduce((s, d) => s + d.spent, 0);
  const totalAvailable = budgetStatus.reduce((s, d) => s + d.available, 0);

  return (
    <div style={{ padding: '20px', height: 'calc(100vh)', overflow: 'auto' }}>
      <h1 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Target size={20} style={{ color: '#EF4444' }} />
        Controlling
      </h1>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        <KpiCard label="Teljes keret" value={formatCurrency(totalPlanned)} color="#F97316" />
        <KpiCard label="Lekötött (PO)" value={formatCurrency(totalCommitted)} color="#F59E0B" />
        <KpiCard label="Felhasznált" value={formatCurrency(totalSpent)} color="#3B82F6" />
        <KpiCard label="Szabad keret" value={formatCurrency(totalAvailable)} color={totalAvailable >= 0 ? '#10B981' : '#EF4444'} />
      </div>

      {/* Quick links */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        <NavCard title="EBITDA" desc="Eredmény osztályonként és időszakonként" icon={<BarChart3 size={20} />} color="#1e3a5f" onClick={() => navigate('/controlling/ebitda')} />
        <NavCard title="Lekötések" desc="Nyitott megrendelések és kötelezettségvállalások" icon={<GitCompareArrows size={20} />} color="#06B6D4" onClick={() => navigate('/controlling/commitment')} />
      </div>

      {/* Department budget table */}
      <h2 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: '#333' }}>Budget státusz osztályonként</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: '#fff', borderRadius: '8px', overflow: 'hidden' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
            {['Osztály', 'Kód', 'Tervezett', 'Lekötött', 'Felhasznált', 'Szabad', 'Kihasználtság'].map(h => (
              <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {budgetStatus.map(dept => (
            <tr key={dept.department_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 10px', fontWeight: 500 }}>{dept.department_name}</td>
              <td style={{ padding: '8px 10px', fontFamily: 'monospace', color: '#666' }}>{dept.department_code}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(dept.planned)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', color: '#F59E0B' }}>{formatCurrency(dept.committed)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', color: '#3B82F6' }}>{formatCurrency(dept.spent)}</td>
              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600, color: dept.available >= 0 ? '#10B981' : '#EF4444' }}>
                {formatCurrency(dept.available)}
              </td>
              <td style={{ padding: '8px 10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ flex: 1, height: '6px', background: '#f3f4f6', borderRadius: '3px', overflow: 'hidden', maxWidth: '100px' }}>
                    <div style={{ width: `${Math.min(dept.utilization_pct, 100)}%`, height: '100%', background: dept.utilization_pct > 90 ? '#EF4444' : dept.utilization_pct > 70 ? '#F59E0B' : '#10B981', borderRadius: '3px' }} />
                  </div>
                  <span style={{ fontSize: '10px', color: '#666' }}>{dept.utilization_pct}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {budgetStatus.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: '16px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', borderTop: `3px solid ${color}` }}>
      <p style={{ margin: 0, fontSize: '11px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</p>
      <p style={{ margin: '6px 0 0', fontSize: '20px', fontWeight: 700, color: '#1a1a1a' }}>{value}</p>
    </div>
  );
}

function NavCard({ title, desc, icon, color, onClick }: { title: string; desc: string; icon: React.ReactNode; color: string; onClick: () => void }) {
  return (
    <div onClick={onClick} style={{
      padding: '16px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px',
      cursor: 'pointer', transition: 'box-shadow 0.15s',
      display: 'flex', alignItems: 'flex-start', gap: '12px',
    }} onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)')}
       onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}>
      <div style={{ color, flexShrink: 0, marginTop: '2px' }}>{icon}</div>
      <div>
        <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#1a1a1a' }}>{title}</p>
        <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#888' }}>{desc}</p>
      </div>
    </div>
  );
}
