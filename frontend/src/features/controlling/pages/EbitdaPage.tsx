import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ChevronDown, ChevronRight, ChevronLeft, Plus, Save, X, TrendingUp, TrendingDown, Minus,
  Check, Lock, History, Copy, Percent, AlertTriangle, CheckCircle, XCircle, Info,
  MessageSquare, CalendarPlus, RefreshCw,
} from 'lucide-react';
import { controllingApi } from '../../../services/api/controlling';
import { departmentsApi } from '../../../services/api/departments';
import { budgetApi } from '../../../services/api/budget';
import { scenariosApi } from '../../../services/api/scenarios';
import { formatCurrency } from '../../../utils/formatters';
import type { PnlRow, PnlChildLine, Department, ValidationResult, AuditLogEntry, BudgetLineComment, Scenario } from '../../../types/controlling';

// Row style configs per P&L key
const ROW_CONFIG: Record<string, { bg: string; border: string; color: string; weight: number; indent: number }> = {
  revenue:       { bg: '#f0fdf4', border: '#86efac', color: '#15803d', weight: 600, indent: 0 },
  cogs:          { bg: '#fff',    border: '#e5e7eb', color: '#374151', weight: 400, indent: 16 },
  gross_profit:  { bg: '#f0fdf4', border: '#22c55e', color: '#15803d', weight: 700, indent: 0 },
  opex:          { bg: '#fff',    border: '#e5e7eb', color: '#374151', weight: 400, indent: 16 },
  ebitda:        { bg: '#eff6ff', border: '#3b82f6', color: '#1d4ed8', weight: 700, indent: 0 },
  depreciation:  { bg: '#fff',    border: '#e5e7eb', color: '#374151', weight: 400, indent: 16 },
  ebit:          { bg: '#eff6ff', border: '#3b82f6', color: '#1e40af', weight: 700, indent: 0 },
  interest:      { bg: '#fff',    border: '#e5e7eb', color: '#374151', weight: 400, indent: 16 },
  pbt:           { bg: '#fefce8', border: '#eab308', color: '#a16207', weight: 700, indent: 0 },
  tax:           { bg: '#fff',    border: '#e5e7eb', color: '#374151', weight: 400, indent: 16 },
  net_income:    { bg: '#faf5ff', border: '#a855f7', color: '#7e22ce', weight: 800, indent: 0 },
};

const CATEGORY_LABELS: Record<string, string> = {
  revenue: 'Bevétel',
  cogs: 'Közvetlen költség',
  opex: 'Működési költség',
  depreciation: 'Értékcsökkenés',
  interest: 'Kamatköltség',
  tax: 'Adó',
};

const STATUS_CONFIG: Record<string, { bg: string; color: string; label: string; border: string }> = {
  draft:    { bg: '#eff6ff', color: '#1d4ed8', label: 'Tervezet', border: '#93c5fd' },
  approved: { bg: '#d1fae5', color: '#065f46', label: 'Jóváhagyva', border: '#6ee7b7' },
  locked:   { bg: '#f3f4f6', color: '#6b7280', label: 'Zárolva', border: '#d1d5db' },
};

export function EbitdaPage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<PnlRow[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [rawPeriods, setRawPeriods] = useState<string[]>([]);
  const [scale, setScale] = useState<'month' | 'quarter' | 'year'>('month');
  const [periodIndex, setPeriodIndex] = useState(0);
  const [deptFilter, setDeptFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Plan type toggle (Feature 3)
  const [planType, setPlanType] = useState<'budget' | 'forecast'>('budget');

  // Scenario (Feature 7)
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState('');
  const [showNewScenarioModal, setShowNewScenarioModal] = useState(false);
  const [newScenarioForm, setNewScenarioForm] = useState({ name: '', description: '', sourceId: '', adjustPct: 0 });

  // Group raw monthly periods by scale
  const groupedPeriods = groupPeriods(rawPeriods, scale);
  const currentGroup = groupedPeriods[periodIndex];
  const periodFilter = scale === 'month' ? (currentGroup?.from || '') : '';
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState<string | null>(null);
  const [addForm, setAddForm] = useState({ account_code: '', account_name: '', planned_amount: 0, department_id: '' });
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  // CFO features state
  const [selectedLines, setSelectedLines] = useState<Set<string>>(new Set());
  const [auditLineId, setAuditLineId] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<AuditLogEntry[]>([]);
  const [showCopyModal, setShowCopyModal] = useState(false);
  const [copySource, setCopySource] = useState('');
  const [showValidation, setShowValidation] = useState<ValidationResult | null>(null);
  const [showAdjustInput, setShowAdjustInput] = useState(false);
  const [adjustPct, setAdjustPct] = useState('');

  // Year plan modal (Feature 2)
  const [showYearPlanModal, setShowYearPlanModal] = useState(false);
  const [yearPlanForm, setYearPlanForm] = useState({ year: new Date().getFullYear() + 1, sourceYear: '', adjustPct: 0 });

  // Forecast modal (Feature 3)
  const [showForecastModal, setShowForecastModal] = useState(false);
  const [forecastForm, setForecastForm] = useState({ adjustPct: 0 });

  // Comments (Feature 5)
  const [commentLineId, setCommentLineId] = useState<string | null>(null);
  const [comments, setComments] = useState<BudgetLineComment[]>([]);
  const [newComment, setNewComment] = useState('');

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);
  useEffect(() => {
    budgetApi.getPeriods().then((p: string[]) => {
      setRawPeriods(p);
      setPeriodIndex(0);
    });
  }, []);

  // Load scenarios on mount
  useEffect(() => {
    scenariosApi.list().then((list: Scenario[]) => {
      setScenarios(list);
      const def = list.find(s => s.is_default);
      if (def) setScenarioId(def.id);
      else if (list.length > 0) setScenarioId(list[0].id);
    });
  }, []);

  const load = useCallback(() => {
    if (!currentGroup) return;
    const params: any = {
      department_id: deptFilter || undefined,
      status: statusFilter || undefined,
      plan_type: planType,
      scenario_id: scenarioId || undefined,
    };
    if (scale === 'month') {
      params.period = currentGroup.from;
    } else {
      params.period_from = currentGroup.from;
      params.period_to = currentGroup.to;
    }
    controllingApi.pnlWaterfall(params).then((data: any) => setRows(data.rows || []));
  }, [deptFilter, statusFilter, currentGroup, scale, planType, scenarioId]);

  useEffect(() => { load(); }, [load]);

  const toggleExpand = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedLines(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = (children: PnlChildLine[]) => {
    const draftIds = children.filter(c => c.status === 'draft').map(c => c.id);
    const allSelected = draftIds.every(id => selectedLines.has(id));
    setSelectedLines(prev => {
      const next = new Set(prev);
      draftIds.forEach(id => allSelected ? next.delete(id) : next.add(id));
      return next;
    });
  };

  // KPI values
  const getVal = (key: string) => rows.find(r => r.key === key);
  const revenue = getVal('revenue');
  const grossProfit = getVal('gross_profit');
  const ebitda = getVal('ebitda');
  const netIncome = getVal('net_income');

  // Available years from rawPeriods
  const availableYears = [...new Set(rawPeriods.map(p => p.split('-')[0]))].sort();

  const handleAddLine = async (category: string) => {
    if (!addForm.account_code || !addForm.account_name || !addForm.department_id) return;
    try {
      await budgetApi.createLine({
        department_id: addForm.department_id,
        account_code: addForm.account_code,
        account_name: addForm.account_name,
        period: currentGroup?.from || new Date().toISOString().slice(0, 7),
        planned_amount: addForm.planned_amount,
        pnl_category: category,
        plan_type: planType,
        scenario_id: scenarioId || undefined,
      });
      setShowAdd(null);
      setAddForm({ account_code: '', account_name: '', planned_amount: 0, department_id: '' });
      load();
    } catch (e: any) {
      alert(e.response?.data?.message || 'Hiba');
    }
  };

  const startEdit = (child: PnlChildLine) => {
    if (child.status !== 'draft') return;
    setEditingCell(child.id);
    setEditValue(String(child.planned));
  };

  const saveEdit = async (lineId: string) => {
    const val = Number(editValue);
    setEditingCell(null);
    try {
      await budgetApi.updateLine(lineId, { planned_amount: val });
      load();
    } catch (e: any) {
      alert(e.response?.data?.message || 'Hiba');
    }
  };

  const cancelEdit = () => {
    setEditingCell(null);
  };

  // Audit trail
  const openAudit = async (lineId: string) => {
    setAuditLineId(lineId);
    try {
      const result = await budgetApi.getLineAudit(lineId, 1, 50);
      setAuditData(result.items || []);
    } catch { setAuditData([]); }
  };

  // Comments (Feature 5)
  const openComments = async (lineId: string) => {
    setCommentLineId(lineId);
    setNewComment('');
    try {
      const result = await budgetApi.getLineComments(lineId, 1, 50);
      setComments(result.items || []);
    } catch { setComments([]); }
  };

  const submitComment = async () => {
    if (!commentLineId || !newComment.trim()) return;
    try {
      await budgetApi.addLineComment(commentLineId, newComment.trim());
      setNewComment('');
      const result = await budgetApi.getLineComments(commentLineId, 1, 50);
      setComments(result.items || []);
      load(); // Refresh comment counts
    } catch (e: any) {
      alert(e.response?.data?.message || 'Hiba');
    }
  };

  // Bulk operations
  const handleBulkApprove = async () => {
    const ids = [...selectedLines];
    try {
      const validation = await budgetApi.validateApprove(ids);
      if (validation.invalid.length > 0 || validation.warnings.length > 0) {
        setShowValidation(validation);
        return;
      }
      await budgetApi.bulkApprove(ids);
      setSelectedLines(new Set());
      load();
    } catch (e: any) { alert(e.response?.data?.message || 'Hiba'); }
  };

  const confirmApprove = async () => {
    if (!showValidation) return;
    try {
      await budgetApi.bulkApprove(showValidation.valid);
      setShowValidation(null);
      setSelectedLines(new Set());
      load();
    } catch (e: any) { alert(e.response?.data?.message || 'Hiba'); }
  };

  const handleBulkLock = async () => {
    try {
      await budgetApi.bulkLock([...selectedLines]);
      setSelectedLines(new Set());
      load();
    } catch (e: any) { alert(e.response?.data?.message || 'Hiba'); }
  };

  const handleBulkAdjust = async () => {
    const pct = parseFloat(adjustPct);
    if (isNaN(pct)) return;
    try {
      await budgetApi.bulkAdjust([...selectedLines], pct);
      setShowAdjustInput(false);
      setAdjustPct('');
      setSelectedLines(new Set());
      load();
    } catch (e: any) { alert(e.response?.data?.message || 'Hiba'); }
  };

  const handleCopyPeriod = async () => {
    if (!copySource || !currentGroup) return;
    try {
      const result = await budgetApi.copyPeriod({
        source_period: copySource,
        target_period: currentGroup.from,
        department_id: deptFilter || undefined,
      });
      setShowCopyModal(false);
      setCopySource('');
      load();
      alert(`${result.created} sor másolva ${copySource} → ${currentGroup.from}`);
    } catch (e: any) { alert(e.response?.data?.message || 'Hiba'); }
  };

  // Year plan (Feature 2)
  const handleCreateYearPlan = async () => {
    try {
      const result = await budgetApi.createYearPlan({
        year: yearPlanForm.year,
        source_year: yearPlanForm.sourceYear ? parseInt(yearPlanForm.sourceYear) : undefined,
        adjustment_pct: yearPlanForm.adjustPct,
        department_id: deptFilter || undefined,
        plan_type: planType,
        scenario_id: scenarioId || undefined,
      });
      setShowYearPlanModal(false);
      setYearPlanForm({ year: new Date().getFullYear() + 1, sourceYear: '', adjustPct: 0 });
      if (result.created === 0) {
        alert('Nem jött létre sor — lehet, hogy a forrás évben nincs adat, vagy már léteznek a cél sorok.');
        return;
      }
      // Reload periods and navigate to new year
      const periods = await budgetApi.getPeriods();
      setRawPeriods(periods);
      // Use scale 'month' for precise navigation to first month of new year
      const targetPeriod = `${result.year}-01`;
      const newGroups = groupPeriods(periods, scale);
      const idx = newGroups.findIndex(g => g.from === targetPeriod || (g.from <= targetPeriod && g.to >= targetPeriod));
      if (idx >= 0) {
        setPeriodIndex(idx);
      } else {
        // Fallback: go to last group (most likely the new year)
        setPeriodIndex(newGroups.length - 1);
      }
      // load() will be triggered by useEffect when periodIndex/rawPeriods change
      alert(`${result.created} sor létrehozva a(z) ${result.year} évre`);
    } catch (e: any) { alert(e.response?.data?.error || 'Hiba'); }
  };

  // Forecast from budget (Feature 3)
  const handleCreateForecast = async () => {
    try {
      const result = await budgetApi.createForecast({
        source_period: currentGroup?.from || undefined,
        department_id: deptFilter || undefined,
        adjustment_pct: forecastForm.adjustPct,
        scenario_id: scenarioId || undefined,
      });
      setShowForecastModal(false);
      setForecastForm({ adjustPct: 0 });
      setPlanType('forecast');
      load();
      alert(`${result.created} forecast sor létrehozva`);
    } catch (e: any) { alert(e.response?.data?.error || 'Hiba'); }
  };

  // Scenario (Feature 7)
  const handleCreateScenario = async () => {
    if (!newScenarioForm.name) return;
    try {
      let result: any;
      if (newScenarioForm.sourceId) {
        result = await scenariosApi.copy({
          source_scenario_id: newScenarioForm.sourceId,
          name: newScenarioForm.name,
          description: newScenarioForm.description || undefined,
          adjustment_pct: newScenarioForm.adjustPct,
        });
      } else {
        result = await scenariosApi.create({
          name: newScenarioForm.name,
          description: newScenarioForm.description || undefined,
        });
      }
      setShowNewScenarioModal(false);
      setNewScenarioForm({ name: '', description: '', sourceId: '', adjustPct: 0 });
      const list = await scenariosApi.list();
      setScenarios(list);
      setScenarioId(result.id);
    } catch (e: any) { alert(e.response?.data?.error || 'Hiba'); }
  };

  return (
    <div style={{ padding: '20px 24px', height: 'calc(100vh)', overflow: 'auto', background: '#f8f9fb' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#111', margin: 0, letterSpacing: '-0.3px' }}>
          Eredménykimutatás (P&L)
        </h1>
        <p style={{ fontSize: '12px', color: '#888', margin: '4px 0 0' }}>Terv vs. Tény — teljes waterfall struktúra</p>
      </div>

      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
        <KpiCard label="Bevétel" plan={revenue?.planned || 0} actual={revenue?.actual || 0} color="#22c55e" icon={<TrendingUp size={16} />} />
        <KpiCard label="Bruttó profit" plan={grossProfit?.planned || 0} actual={grossProfit?.actual || 0} color="#3b82f6" pct={grossProfit?.margin_pct} icon={<TrendingUp size={16} />} />
        <KpiCard label="EBITDA" plan={ebitda?.planned || 0} actual={ebitda?.actual || 0} color="#8b5cf6" pct={ebitda?.margin_pct} icon={ebitda && ebitda.actual >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />} />
        <KpiCard label="Nettó eredmény" plan={netIncome?.planned || 0} actual={netIncome?.actual || 0} color="#a855f7" pct={netIncome?.margin_pct} icon={netIncome && netIncome.actual >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />} />
      </div>

      {/* PERIOD TOOLBAR */}
      <div style={{
        background: '#fff', borderRadius: '12px', border: '1px solid #e5e7eb',
        padding: '12px 20px', marginBottom: '16px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap',
      }}
        tabIndex={0}
        onKeyDown={e => {
          if (e.key === 'ArrowLeft') setPeriodIndex(i => Math.max(0, i - 1));
          if (e.key === 'ArrowRight') setPeriodIndex(i => Math.min(groupedPeriods.length - 1, i + 1));
        }}
      >
        {/* Scale selector */}
        <div style={{
          display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '3px',
        }}>
          {(['month', 'quarter', 'year'] as const).map(s => (
            <button
              key={s}
              onClick={() => { setScale(s); setPeriodIndex(0); }}
              style={{
                padding: '6px 16px', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600,
                background: scale === s ? '#fff' : 'transparent',
                color: scale === s ? '#111' : '#888',
                cursor: 'pointer',
                boxShadow: scale === s ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              {{ month: 'Hónap', quarter: 'Negyedév', year: 'Év' }[s]}
            </button>
          ))}
        </div>

        {/* Separator */}
        <div style={{ width: '1px', height: '28px', background: '#e5e7eb' }} />

        {/* Budget / Forecast toggle (Feature 3) */}
        <div style={{
          display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '3px',
        }}>
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
                transition: 'all 0.15s ease',
              }}
            >
              {pt === 'budget' ? 'Budget' : 'Forecast'}
            </button>
          ))}
        </div>

        {/* Separator */}
        <div style={{ width: '1px', height: '28px', background: '#e5e7eb' }} />

        {/* Scenario selector (Feature 7) */}
        <select
          value={scenarioId}
          onChange={e => setScenarioId(e.target.value)}
          style={filterStyle}
        >
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>{s.name}{s.is_default ? ' (alap)' : ''}</option>
          ))}
        </select>
        <button
          onClick={() => setShowNewScenarioModal(true)}
          style={{ ...toolBtnStyle, padding: '6px 10px' }}
          title="Új szcenárió"
        >
          <Plus size={13} />
        </button>

        {/* Separator */}
        <div style={{ width: '1px', height: '28px', background: '#e5e7eb' }} />

        {/* Period navigator */}
        <button
          onClick={() => setPeriodIndex(i => Math.max(0, i - 1))}
          disabled={periodIndex <= 0}
          style={{
            width: '32px', height: '32px', border: '1px solid #e5e7eb', borderRadius: '8px',
            background: periodIndex > 0 ? '#fff' : '#f9fafb',
            cursor: periodIndex > 0 ? 'pointer' : 'default',
            color: periodIndex > 0 ? '#333' : '#d1d5db',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.1s',
          }}
        >
          <ChevronLeft size={16} />
        </button>

        <div style={{ textAlign: 'center', minWidth: '180px' }}>
          <div style={{ fontSize: '16px', fontWeight: 800, color: '#111', letterSpacing: '-0.3px' }}>
            {currentGroup ? currentGroup.label : '—'}
          </div>
          {currentGroup && scale !== 'month' && (
            <div style={{ fontSize: '11px', color: '#888', marginTop: '1px' }}>
              {formatRangeSubtitle(currentGroup.from, currentGroup.to)}
            </div>
          )}
        </div>

        <button
          onClick={() => setPeriodIndex(i => Math.min(groupedPeriods.length - 1, i + 1))}
          disabled={periodIndex >= groupedPeriods.length - 1}
          style={{
            width: '32px', height: '32px', border: '1px solid #e5e7eb', borderRadius: '8px',
            background: periodIndex < groupedPeriods.length - 1 ? '#fff' : '#f9fafb',
            cursor: periodIndex < groupedPeriods.length - 1 ? 'pointer' : 'default',
            color: periodIndex < groupedPeriods.length - 1 ? '#333' : '#d1d5db',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.1s',
          }}
        >
          <ChevronRight size={16} />
        </button>

        <span style={{
          fontSize: '10px', color: '#aaa', background: '#f3f4f6', padding: '2px 8px',
          borderRadius: '4px', fontWeight: 600, fontVariantNumeric: 'tabular-nums',
        }}>
          {groupedPeriods.length > 0 ? `${periodIndex + 1} / ${groupedPeriods.length}` : ''}
        </span>

        {/* Separator */}
        <div style={{ width: '1px', height: '28px', background: '#e5e7eb' }} />

        {/* Filters */}
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={filterStyle}>
          <option value="">Konszolidált</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={filterStyle}>
          <option value="">Minden verzió</option>
          <option value="draft">Tervezet</option>
          <option value="approved">Jóváhagyott</option>
          <option value="locked">Zárolt</option>
        </select>

        <div style={{ flex: 1 }} />

        {/* Forecast creation button (Feature 3) */}
        {planType === 'budget' && (
          <button onClick={() => setShowForecastModal(true)} style={toolBtnStyle} title="Forecast létrehozása budget-ből">
            <RefreshCw size={13} /> Forecast
          </button>
        )}

        <button onClick={() => setShowYearPlanModal(true)} style={toolBtnStyle} title="Új éves terv indítása">
          <CalendarPlus size={13} /> Új időszak
        </button>

        <button onClick={() => setShowCopyModal(true)} style={toolBtnStyle} title="Másolás korábbi időszakból">
          <Copy size={13} /> Másolás
        </button>
      </div>

      {/* P&L Table */}
      <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e5e7eb', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '28px 1fr 140px 140px 140px 80px',
          background: '#f9fafb', borderBottom: '2px solid #e5e7eb',
        }}>
          <div style={{ padding: '10px 4px' }} />
          {['', 'TERV', 'TÉNY', 'ELTÉRÉS', 'VAR %'].map((h, i) => (
            <div key={h + i} style={{
              padding: '10px 14px', fontSize: '10px', fontWeight: 700, color: '#6b7280',
              textTransform: 'uppercase', letterSpacing: '0.5px',
              textAlign: i > 0 ? 'right' : 'left',
            }}>{h}</div>
          ))}
        </div>

        {/* Rows */}
        {rows.map((row) => {
          const cfg = ROW_CONFIG[row.key] || ROW_CONFIG.opex;
          const isExpanded = expanded.has(row.key);
          const hasChildren = row.children && row.children.length > 0;

          return (
            <div key={row.key}>
              {row.is_subtotal && (
                <div style={{ height: '1px', background: cfg.border, margin: '0 14px' }} />
              )}

              {/* Main row */}
              <div
                style={{
                  display: 'grid', gridTemplateColumns: '28px 1fr 140px 140px 140px 80px',
                  background: cfg.bg,
                  borderLeft: `3px solid ${cfg.border}`,
                  borderBottom: row.is_subtotal ? `2px solid ${cfg.border}` : '1px solid #f3f4f6',
                  cursor: hasChildren && !row.is_subtotal ? 'pointer' : 'default',
                  transition: 'background 0.1s',
                }}
                onClick={() => hasChildren && !row.is_subtotal && toggleExpand(row.key)}
                onMouseEnter={e => { if (!row.is_subtotal) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={e => { if (!row.is_subtotal) e.currentTarget.style.background = cfg.bg; }}
              >
                <div style={{ padding: '10px 4px' }} />
                {/* Label */}
                <div style={{
                  padding: '10px 14px', paddingLeft: `${14 + cfg.indent}px`,
                  display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                  {hasChildren && !row.is_subtotal && (
                    isExpanded ? <ChevronDown size={13} color="#999" /> : <ChevronRight size={13} color="#999" />
                  )}
                  {row.is_subtotal && <Minus size={13} color={cfg.color} />}
                  <span style={{ fontSize: row.is_subtotal ? '13px' : '12px', fontWeight: cfg.weight, color: cfg.color }}>
                    {row.label}
                  </span>
                  {row.is_subtotal && row.margin_pct > 0 && (
                    <span style={{
                      fontSize: '10px', color: '#888', background: '#f3f4f6',
                      padding: '1px 6px', borderRadius: '3px', fontWeight: 500,
                    }}>
                      {row.margin_pct}% margin
                    </span>
                  )}
                </div>

                <div style={{ padding: '10px 14px', textAlign: 'right', fontSize: '13px', fontWeight: cfg.weight, color: cfg.color, fontVariantNumeric: 'tabular-nums' }}>
                  {formatCurrency(row.planned)}
                </div>
                <div style={{ padding: '10px 14px', textAlign: 'right', fontSize: '13px', fontWeight: row.is_subtotal ? 700 : 400, color: row.is_subtotal ? cfg.color : '#374151', fontVariantNumeric: 'tabular-nums' }}>
                  {formatCurrency(row.actual)}
                </div>
                <div style={{ padding: '10px 14px', textAlign: 'right', fontSize: '13px', fontWeight: 500, color: row.variance >= 0 ? '#16a34a' : '#dc2626', fontVariantNumeric: 'tabular-nums' }}>
                  {row.variance >= 0 ? '+' : ''}{formatCurrency(row.variance)}
                </div>
                <div style={{ padding: '10px 14px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: row.variance_pct >= 0 ? '#16a34a' : '#dc2626' }}>
                  {row.variance_pct >= 0 ? '+' : ''}{row.variance_pct}%
                </div>
              </div>

              {/* Expanded children */}
              {isExpanded && hasChildren && (
                <div style={{ background: '#fafbfc' }}>
                  {/* Select all for category */}
                  {row.children.some(c => c.status === 'draft') && (
                    <div style={{ padding: '4px 14px 4px 6px', display: 'flex', alignItems: 'center', gap: '6px', borderBottom: '1px solid #f0f1f3', fontSize: '10px', color: '#888' }}>
                      <input
                        type="checkbox"
                        checked={row.children.filter(c => c.status === 'draft').every(c => selectedLines.has(c.id))}
                        onChange={() => toggleSelectAll(row.children)}
                        style={{ width: '14px', height: '14px', cursor: 'pointer' }}
                      />
                      <span>Összes tervezet kijelölése</span>
                    </div>
                  )}

                  {row.children.map((child: PnlChildLine) => {
                    const sc = STATUS_CONFIG[child.status] || STATUS_CONFIG.draft;
                    const isDraft = child.status === 'draft';
                    const commentCount = child.comment_count || 0;
                    return (
                      <div key={child.id} style={{
                        display: 'grid', gridTemplateColumns: '28px 1fr 140px 140px 140px 80px',
                        borderBottom: '1px solid #f0f1f3',
                        borderLeft: `3px solid ${isDraft ? '#93c5fd' : child.status === 'approved' ? '#6ee7b7' : '#e5e7eb'}`,
                        background: child.status === 'locked' ? '#fafafa' : 'transparent',
                      }}>
                        {/* Checkbox */}
                        <div style={{ padding: '7px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {isDraft && (
                            <input
                              type="checkbox"
                              checked={selectedLines.has(child.id)}
                              onChange={() => toggleSelect(child.id)}
                              onClick={e => e.stopPropagation()}
                              style={{ width: '14px', height: '14px', cursor: 'pointer' }}
                            />
                          )}
                          {child.status === 'locked' && <Lock size={10} color="#9ca3af" />}
                          {child.status === 'approved' && <Check size={10} color="#10b981" />}
                        </div>

                        {/* Label + status badge + comment + audit button */}
                        <div style={{ padding: '7px 14px 7px 12px', fontSize: '11px', color: '#555', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{
                            padding: '1px 6px', borderRadius: '3px', fontSize: '9px', fontWeight: 600,
                            background: sc.bg, color: sc.color, border: `1px solid ${sc.border}`,
                            whiteSpace: 'nowrap',
                          }}>{sc.label}</span>
                          <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#999', background: '#f3f4f6', padding: '1px 4px', borderRadius: '2px' }}>
                            {child.account_code}
                          </span>
                          <span>{child.account_name}</span>
                          {child.department_name && (
                            <span style={{ fontSize: '10px', color: '#aaa' }}>({child.department_name})</span>
                          )}
                          <div style={{ flex: 1 }} />
                          <span style={{ fontSize: '9px', color: '#bbb' }} title={`Módosította: ${child.creator_name || '?'} — ${new Date(child.updated_at).toLocaleString('hu')}`}>
                            {child.creator_name || ''}
                          </span>
                          {/* Comment button (Feature 5) */}
                          <button
                            onClick={e => { e.stopPropagation(); openComments(child.id); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: commentCount > 0 ? '#3b82f6' : '#bbb', display: 'flex', alignItems: 'center', gap: '2px', position: 'relative' }}
                            title="Megjegyzések"
                          >
                            <MessageSquare size={12} />
                            {commentCount > 0 && (
                              <span style={{
                                fontSize: '8px', fontWeight: 700, color: '#fff', background: '#3b82f6',
                                borderRadius: '6px', padding: '0 4px', minWidth: '14px', textAlign: 'center',
                                lineHeight: '14px',
                              }}>
                                {commentCount}
                              </span>
                            )}
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); openAudit(child.id); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: '#bbb', display: 'flex' }}
                            title="Előzmények"
                          >
                            <History size={12} />
                          </button>
                        </div>

                        {/* Plan (editable if draft) */}
                        <div
                          onClick={isDraft && editingCell !== child.id ? (e) => { e.stopPropagation(); startEdit(child); } : undefined}
                          style={{
                            padding: '7px 14px', textAlign: 'right', fontSize: '12px', fontVariantNumeric: 'tabular-nums',
                            cursor: isDraft && editingCell !== child.id ? 'pointer' : 'default',
                            color: isDraft ? '#374151' : '#9ca3af',
                            background: 'transparent', transition: 'background 0.1s',
                            borderRadius: '4px',
                          }}
                          onMouseEnter={isDraft && editingCell !== child.id ? e => { e.currentTarget.style.background = '#dbeafe'; } : undefined}
                          onMouseLeave={isDraft ? e => { e.currentTarget.style.background = 'transparent'; } : undefined}
                          title={isDraft ? 'Kattints a szerkesztéshez' : `${sc.label} — nem szerkeszthető`}
                        >
                          {editingCell === child.id ? (
                            <input
                              autoFocus
                              type="number"
                              value={editValue}
                              onChange={e => setEditValue(e.target.value)}
                              onBlur={() => saveEdit(child.id)}
                              onKeyDown={e => { if (e.key === 'Enter') saveEdit(child.id); if (e.key === 'Escape') setEditingCell(null); }}
                              style={{
                                width: '110px', padding: '2px 6px', border: '2px solid #3b82f6', borderRadius: '4px',
                                fontSize: '12px', textAlign: 'right', outline: 'none', background: '#eff6ff',
                              }}
                              onClick={e => e.stopPropagation()}
                            />
                          ) : (
                            formatCurrency(child.planned)
                          )}
                        </div>

                        <div style={{ padding: '7px 14px', textAlign: 'right', fontSize: '12px', color: '#666', fontVariantNumeric: 'tabular-nums' }}>
                          {formatCurrency(child.actual)}
                        </div>
                        <div style={{ padding: '7px 14px', textAlign: 'right', fontSize: '12px', color: child.variance >= 0 ? '#16a34a' : '#dc2626', fontVariantNumeric: 'tabular-nums' }}>
                          {child.variance >= 0 ? '+' : ''}{formatCurrency(child.variance)}
                        </div>
                        <div style={{ padding: '7px 14px', textAlign: 'right', fontSize: '11px', color: child.variance_pct >= 0 ? '#16a34a' : '#dc2626' }}>
                          {child.variance_pct >= 0 ? '+' : ''}{child.variance_pct}%
                        </div>
                      </div>
                    );
                  })}

                  {/* Add new line button */}
                  {showAdd === row.key ? (
                    <div style={{ padding: '8px 14px 8px 48px', display: 'flex', gap: '6px', alignItems: 'center', borderBottom: '1px solid #f0f1f3' }}>
                      <select value={addForm.department_id} onChange={e => setAddForm({ ...addForm, department_id: e.target.value })}
                        style={{ ...miniInput, minWidth: '120px' }}>
                        <option value="">Osztály</option>
                        {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                      </select>
                      <input placeholder="Kód" value={addForm.account_code} onChange={e => setAddForm({ ...addForm, account_code: e.target.value })} style={{ ...miniInput, width: '70px' }} />
                      <input placeholder="Megnevezés" value={addForm.account_name} onChange={e => setAddForm({ ...addForm, account_name: e.target.value })} style={{ ...miniInput, flex: 1 }} />
                      <input type="number" placeholder="Összeg" value={addForm.planned_amount || ''} onChange={e => setAddForm({ ...addForm, planned_amount: Number(e.target.value) })} style={{ ...miniInput, width: '100px', textAlign: 'right' }} />
                      <button onClick={() => handleAddLine(row.key)} style={{ padding: '3px 10px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 500 }}>
                        <Save size={11} />
                      </button>
                      <button onClick={() => setShowAdd(null)} style={{ padding: '3px 6px', background: 'none', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer', color: '#999' }}>
                        <X size={11} />
                      </button>
                    </div>
                  ) : (
                    <div
                      onClick={(e) => { e.stopPropagation(); setShowAdd(row.key); }}
                      style={{
                        padding: '6px 14px 6px 48px', fontSize: '11px', color: '#3b82f6', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: '4px', borderBottom: '1px solid #f0f1f3',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#eff6ff'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <Plus size={11} /> Új {CATEGORY_LABELS[row.key] || ''} sor hozzáadása
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Waterfall bar chart */}
      {rows.length > 0 && (
        <div style={{ marginTop: '24px', background: '#fff', borderRadius: '10px', border: '1px solid #e5e7eb', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#333', marginBottom: '16px' }}>P&L Waterfall — Terv</h3>
          <WaterfallChart rows={rows} />
        </div>
      )}

      {/* Legend */}
      <div style={{ marginTop: '12px', display: 'flex', gap: '16px', fontSize: '10px', color: '#888', padding: '0 4px', flexWrap: 'wrap' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#93c5fd', display: 'inline-block' }} />
          Tervezet (szerkeszthető)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#6ee7b7', display: 'inline-block' }} />
          Jóváhagyott
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#d1d5db', display: 'inline-block' }} />
          Zárolt (végleges)
        </span>
        <span>Subtotal sorok automatikusan számítódnak</span>
        <span>Margin % = sor / bevétel</span>
      </div>

      {/* BULK ACTION BAR */}
      {selectedLines.size > 0 && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0,
          background: '#1e293b', color: '#fff', padding: '12px 24px',
          display: 'flex', alignItems: 'center', gap: '12px',
          boxShadow: '0 -4px 20px rgba(0,0,0,0.15)', zIndex: 100,
        }}>
          <span style={{ fontSize: '13px', fontWeight: 600 }}>
            {selectedLines.size} sor kijelölve
          </span>
          <div style={{ flex: 1 }} />

          <button onClick={handleBulkApprove} style={bulkBtnStyle('#22c55e')}>
            <Check size={13} /> Jóváhagyás
          </button>
          <button onClick={handleBulkLock} style={bulkBtnStyle('#3b82f6')}>
            <Lock size={13} /> Zárolás
          </button>

          {showAdjustInput ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                autoFocus
                type="number"
                placeholder="+/- %"
                value={adjustPct}
                onChange={e => setAdjustPct(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleBulkAdjust(); if (e.key === 'Escape') setShowAdjustInput(false); }}
                style={{ width: '80px', padding: '6px 8px', borderRadius: '4px', border: '1px solid #475569', background: '#334155', color: '#fff', fontSize: '12px', textAlign: 'right' }}
              />
              <button onClick={handleBulkAdjust} style={bulkBtnStyle('#f59e0b')}>OK</button>
              <button onClick={() => setShowAdjustInput(false)} style={{ ...bulkBtnStyle('#6b7280'), padding: '6px 8px' }}><X size={12} /></button>
            </div>
          ) : (
            <button onClick={() => setShowAdjustInput(true)} style={bulkBtnStyle('#f59e0b')}>
              <Percent size={13} /> Módosítás
            </button>
          )}

          <button onClick={() => setSelectedLines(new Set())} style={{ ...bulkBtnStyle('#6b7280'), marginLeft: '8px' }}>
            <X size={13} /> Mégse
          </button>
        </div>
      )}

      {/* AUDIT TRAIL PANEL */}
      {auditLineId && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '380px',
          background: '#fff', borderLeft: '1px solid #e5e7eb',
          boxShadow: '-4px 0 20px rgba(0,0,0,0.08)', zIndex: 200,
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <History size={16} /> Előzmények
            </h3>
            <button onClick={() => setAuditLineId(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999' }}>
              <X size={18} />
            </button>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
            {auditData.length === 0 ? (
              <p style={{ color: '#999', fontSize: '12px', textAlign: 'center', marginTop: '40px' }}>Nincs előzmény</p>
            ) : (
              <div style={{ position: 'relative', paddingLeft: '20px' }}>
                {/* Timeline line */}
                <div style={{ position: 'absolute', left: '7px', top: '4px', bottom: '4px', width: '2px', background: '#e5e7eb' }} />
                {auditData.map((entry) => (
                  <div key={entry.id} style={{ position: 'relative', marginBottom: '16px' }}>
                    {/* Timeline dot */}
                    <div style={{
                      position: 'absolute', left: '-16px', top: '4px', width: '10px', height: '10px',
                      borderRadius: '50%', border: '2px solid #fff',
                      background: entry.action.includes('approve') ? '#22c55e' : entry.action.includes('lock') ? '#3b82f6' : entry.action.includes('create') ? '#f59e0b' : '#8b5cf6',
                      boxShadow: '0 0 0 2px #e5e7eb',
                    }} />
                    <div>
                      <AuditActionLabel action={entry.action} />
                      <p style={{ fontSize: '10px', color: '#999', margin: '2px 0' }}>
                        {entry.user_name || 'Rendszer'} — {new Date(entry.created_at).toLocaleString('hu')}
                      </p>
                      {entry.details && Object.keys(entry.details).length > 0 && (
                        <AuditDetails details={entry.details} />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* COMMENT PANEL (Feature 5) */}
      {commentLineId && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '380px',
          background: '#fff', borderLeft: '1px solid #e5e7eb',
          boxShadow: '-4px 0 20px rgba(0,0,0,0.08)', zIndex: 200,
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MessageSquare size={16} /> Megjegyzések
            </h3>
            <button onClick={() => setCommentLineId(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999' }}>
              <X size={18} />
            </button>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
            {comments.length === 0 ? (
              <p style={{ color: '#999', fontSize: '12px', textAlign: 'center', marginTop: '40px' }}>Nincs megjegyzés</p>
            ) : (
              comments.map(c => (
                <div key={c.id} style={{ marginBottom: '12px', padding: '10px 12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #f0f1f3' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 600, color: '#333' }}>{c.user_name || 'Ismeretlen'}</span>
                    <span style={{ fontSize: '10px', color: '#999' }}>{new Date(c.created_at).toLocaleString('hu')}</span>
                  </div>
                  <p style={{ fontSize: '12px', color: '#555', margin: 0, whiteSpace: 'pre-wrap' }}>{c.text}</p>
                </div>
              ))
            )}
          </div>
          <div style={{ padding: '12px 20px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '8px' }}>
            <textarea
              value={newComment}
              onChange={e => setNewComment(e.target.value)}
              placeholder="Megjegyzés hozzáadása..."
              style={{
                flex: 1, padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px',
                fontSize: '12px', resize: 'none', height: '60px', outline: 'none',
              }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); } }}
            />
            <button
              onClick={submitComment}
              disabled={!newComment.trim()}
              style={{
                padding: '8px 14px', background: newComment.trim() ? '#3b82f6' : '#d1d5db',
                color: '#fff', border: 'none', borderRadius: '6px', cursor: newComment.trim() ? 'pointer' : 'default',
                fontSize: '12px', fontWeight: 600, alignSelf: 'flex-end',
              }}
            >
              Küldés
            </button>
          </div>
        </div>
      )}

      {/* VALIDATION MODAL */}
      {showValidation && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '500px', maxHeight: '80vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="#f59e0b" /> Jóváhagyás ellenőrzés
            </h3>

            {showValidation.valid.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <p style={{ fontSize: '12px', fontWeight: 600, color: '#065f46', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle size={13} /> {showValidation.valid.length} sor jóváhagyható
                </p>
              </div>
            )}

            {showValidation.invalid.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <p style={{ fontSize: '12px', fontWeight: 600, color: '#991b1b', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <XCircle size={13} /> {showValidation.invalid.length} sor nem hagyható jóvá
                </p>
                {showValidation.invalid.map(inv => (
                  <div key={inv.id} style={{ fontSize: '11px', color: '#666', padding: '4px 0 4px 20px' }}>
                    <span style={{ fontFamily: 'monospace', color: '#999' }}>{inv.id.slice(0, 8)}</span>: {inv.reasons.join(', ')}
                  </div>
                ))}
              </div>
            )}

            {showValidation.warnings.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <p style={{ fontSize: '12px', fontWeight: 600, color: '#92400e', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Info size={13} /> {showValidation.warnings.length} figyelmeztetés
                </p>
                {showValidation.warnings.map(w => (
                  <div key={w.id} style={{ fontSize: '11px', color: '#666', padding: '4px 0 4px 20px' }}>
                    <span style={{ fontFamily: 'monospace', color: '#999' }}>{w.id.slice(0, 8)}</span>: {w.warnings.join(', ')}
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => setShowValidation(null)} style={{ padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', cursor: 'pointer', fontSize: '12px' }}>
                Mégse
              </button>
              {showValidation.valid.length > 0 && (
                <button onClick={confirmApprove} style={{ padding: '8px 16px', border: 'none', borderRadius: '6px', background: '#22c55e', color: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                  {showValidation.valid.length} sor jóváhagyása
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* COPY PERIOD MODAL */}
      {showCopyModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '400px', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Copy size={18} /> Másolás korábbi időszakból
            </h3>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '11px', fontWeight: 600, color: '#555', display: 'block', marginBottom: '4px' }}>Forrás időszak</label>
              <input type="month" value={copySource} onChange={e => setCopySource(e.target.value)} style={{ ...filterStyle, width: '100%' }} />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '11px', fontWeight: 600, color: '#555', display: 'block', marginBottom: '4px' }}>Cél időszak</label>
              <input type="text" value={currentGroup?.label || ''} disabled style={{ ...filterStyle, width: '100%', background: '#f3f4f6' }} />
              {!currentGroup && (
                <p style={{ fontSize: '10px', color: '#dc2626', margin: '4px 0 0' }}>Először válassz cél időszakot a navigátorban</p>
              )}
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowCopyModal(false)} style={{ padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#fff', cursor: 'pointer', fontSize: '12px' }}>
                Mégse
              </button>
              <button onClick={handleCopyPeriod} disabled={!copySource || !currentGroup} style={{
                padding: '8px 16px', border: 'none', borderRadius: '6px', background: !copySource || !currentGroup ? '#d1d5db' : '#3b82f6', color: '#fff', cursor: !copySource || !currentGroup ? 'default' : 'pointer', fontSize: '12px', fontWeight: 600,
              }}>
                Másolás
              </button>
            </div>
          </div>
        </div>
      )}

      {/* YEAR PLAN MODAL (Feature 2) */}
      {showYearPlanModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '420px', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CalendarPlus size={18} /> Új éves terv
            </h3>

            <div style={{ marginBottom: '12px' }}>
              <label style={labelStyle}>Cél év</label>
              <input type="number" value={yearPlanForm.year} onChange={e => setYearPlanForm({ ...yearPlanForm, year: Number(e.target.value) })}
                style={{ ...filterStyle, width: '100%' }} />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={labelStyle}>Forrás év (opcionális)</label>
              <select value={yearPlanForm.sourceYear} onChange={e => setYearPlanForm({ ...yearPlanForm, sourceYear: e.target.value })}
                style={{ ...filterStyle, width: '100%' }}>
                <option value="">— Üres terv —</option>
                {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>

            {yearPlanForm.sourceYear && (
              <div style={{ marginBottom: '12px' }}>
                <label style={labelStyle}>Korrekció (%)</label>
                <input type="number" value={yearPlanForm.adjustPct} onChange={e => setYearPlanForm({ ...yearPlanForm, adjustPct: Number(e.target.value) })}
                  style={{ ...filterStyle, width: '100%' }} placeholder="+5 = 5%-os növekedés" />
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => setShowYearPlanModal(false)} style={modalCancelBtn}>Mégse</button>
              <button onClick={handleCreateYearPlan} style={modalPrimaryBtn}>Létrehozás</button>
            </div>
          </div>
        </div>
      )}

      {/* FORECAST MODAL (Feature 3) */}
      {showForecastModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '400px', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <RefreshCw size={18} /> Forecast létrehozása
            </h3>
            <p style={{ fontSize: '12px', color: '#666', margin: '0 0 16px' }}>
              Budget sorok másolása forecast-ként a jelenlegi időszakra ({currentGroup?.label}).
            </p>

            <div style={{ marginBottom: '16px' }}>
              <label style={labelStyle}>Korrekció (%)</label>
              <input type="number" value={forecastForm.adjustPct} onChange={e => setForecastForm({ adjustPct: Number(e.target.value) })}
                style={{ ...filterStyle, width: '100%' }} placeholder="0 = azonos összeg" />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowForecastModal(false)} style={modalCancelBtn}>Mégse</button>
              <button onClick={handleCreateForecast} style={{ ...modalPrimaryBtn, background: '#7c3aed' }}>Forecast létrehozása</button>
            </div>
          </div>
        </div>
      )}

      {/* NEW SCENARIO MODAL (Feature 7) */}
      {showNewScenarioModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '440px', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 700 }}>Új szcenárió</h3>

            <div style={{ marginBottom: '12px' }}>
              <label style={labelStyle}>Név</label>
              <input value={newScenarioForm.name} onChange={e => setNewScenarioForm({ ...newScenarioForm, name: e.target.value })}
                style={{ ...filterStyle, width: '100%' }} placeholder="pl. Optimista" />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={labelStyle}>Leírás (opcionális)</label>
              <input value={newScenarioForm.description} onChange={e => setNewScenarioForm({ ...newScenarioForm, description: e.target.value })}
                style={{ ...filterStyle, width: '100%' }} />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={labelStyle}>Forrás szcenárió (opcionális)</label>
              <select value={newScenarioForm.sourceId} onChange={e => setNewScenarioForm({ ...newScenarioForm, sourceId: e.target.value })}
                style={{ ...filterStyle, width: '100%' }}>
                <option value="">— Üres szcenárió —</option>
                {scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>

            {newScenarioForm.sourceId && (
              <div style={{ marginBottom: '12px' }}>
                <label style={labelStyle}>Korrekció (%)</label>
                <input type="number" value={newScenarioForm.adjustPct} onChange={e => setNewScenarioForm({ ...newScenarioForm, adjustPct: Number(e.target.value) })}
                  style={{ ...filterStyle, width: '100%' }} />
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => setShowNewScenarioModal(false)} style={modalCancelBtn}>Mégse</button>
              <button onClick={handleCreateScenario} disabled={!newScenarioForm.name} style={{
                ...modalPrimaryBtn, background: newScenarioForm.name ? '#3b82f6' : '#d1d5db',
                cursor: newScenarioForm.name ? 'pointer' : 'default',
              }}>Létrehozás</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* Audit helpers */
const AUDIT_ACTION_LABELS: Record<string, { label: string; color: string }> = {
  'budget_line.create': { label: 'Létrehozva', color: '#f59e0b' },
  'budget_line.update': { label: 'Módosítva', color: '#8b5cf6' },
  'budget_line.approve': { label: 'Jóváhagyva', color: '#22c55e' },
  'budget_line.lock': { label: 'Zárolva', color: '#3b82f6' },
  'budget_line.copy': { label: 'Másolva', color: '#06b6d4' },
  'budget_line.adjust': { label: '% Módosítás', color: '#f59e0b' },
  'budget_line.comment': { label: 'Megjegyzés', color: '#8b5cf6' },
  'budget_line.create_year_plan': { label: 'Éves terv', color: '#06b6d4' },
  'budget_line.create_forecast': { label: 'Forecast', color: '#7c3aed' },
};

function AuditActionLabel({ action }: { action: string }) {
  const cfg = AUDIT_ACTION_LABELS[action] || { label: action, color: '#666' };
  return (
    <span style={{ fontSize: '12px', fontWeight: 600, color: cfg.color }}>{cfg.label}</span>
  );
}

function AuditDetails({ details }: { details: Record<string, any> }) {
  if (details.old && details.new) {
    return (
      <div style={{ fontSize: '10px', color: '#666', marginTop: '4px', background: '#f9fafb', padding: '6px 8px', borderRadius: '4px' }}>
        {Object.keys(details.new).map(k => (
          <div key={k}>
            <span style={{ color: '#999' }}>{k}:</span>{' '}
            <span style={{ color: '#dc2626', textDecoration: 'line-through' }}>{String(details.old[k] ?? '')}</span>
            {' → '}
            <span style={{ color: '#16a34a', fontWeight: 600 }}>{String(details.new[k])}</span>
          </div>
        ))}
      </div>
    );
  }
  if (details.old_amount !== undefined && details.new_amount !== undefined) {
    return (
      <div style={{ fontSize: '10px', color: '#666', marginTop: '4px', background: '#f9fafb', padding: '6px 8px', borderRadius: '4px' }}>
        {formatCurrency(details.old_amount)} → {formatCurrency(details.new_amount)} ({details.percentage > 0 ? '+' : ''}{details.percentage}%)
      </div>
    );
  }
  if (details.source_period) {
    return (
      <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
        Forrás: {details.source_period}
      </div>
    );
  }
  return null;
}

/* KPI Card */
function KpiCard({ label, plan, actual, color, pct, icon }: {
  label: string; plan: number; actual: number; color: string; pct?: number; icon: React.ReactNode;
}) {
  const variance = plan - actual;
  return (
    <div style={{
      padding: '14px 16px', background: '#fff', border: '1px solid #e5e7eb',
      borderRadius: '10px', borderTop: `3px solid ${color}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontSize: '10px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>{label}</span>
        <span style={{ color }}>{icon}</span>
      </div>
      <div style={{ fontSize: '18px', fontWeight: 800, color: '#111', fontVariantNumeric: 'tabular-nums', marginBottom: '4px' }}>
        {formatCurrency(plan)}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', color: '#888' }}>Tény: {formatCurrency(actual)}</span>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {pct !== undefined && pct > 0 && (
            <span style={{ fontSize: '10px', color, fontWeight: 700, background: `${color}15`, padding: '1px 5px', borderRadius: '3px' }}>
              {pct}%
            </span>
          )}
          <span style={{ fontSize: '10px', fontWeight: 600, color: variance >= 0 ? '#16a34a' : '#dc2626' }}>
            {variance >= 0 ? '+' : ''}{formatCurrency(variance)}
          </span>
        </div>
      </div>
    </div>
  );
}

/* Waterfall Chart */
function WaterfallChart({ rows }: { rows: PnlRow[] }) {
  const waterfallKeys = ['revenue', 'cogs', 'gross_profit', 'opex', 'ebitda', 'depreciation', 'ebit', 'interest', 'pbt', 'tax', 'net_income'];
  const items = waterfallKeys.map(k => rows.find(r => r.key === k)).filter(Boolean) as PnlRow[];
  if (items.length === 0) return null;

  const shortLabels: Record<string, string> = {
    revenue: 'Bevétel', cogs: 'COGS', gross_profit: 'Bruttó profit',
    opex: 'OpEx', ebitda: 'EBITDA', depreciation: 'D&A',
    ebit: 'EBIT', interest: 'Kamat', pbt: 'PBT',
    tax: 'Adó', net_income: 'Nettó',
  };

  const subtotalKeys = new Set(['revenue', 'gross_profit', 'ebitda', 'ebit', 'pbt', 'net_income']);

  // Build waterfall: running total, costs float
  let running = 0;
  const data = items.map(item => {
    const label = shortLabels[item.key] || item.key;
    const val = item.planned;

    if (subtotalKeys.has(item.key)) {
      running = val;
      return { name: label, base: 0, value: val, raw: val, isSubtotal: true, isCost: false, key: item.key };
    }

    const deduction = Math.abs(val);
    const newRunning = running - deduction;
    const barBase = Math.min(running, newRunning);
    running = newRunning;
    return { name: label, base: barBase, value: deduction, raw: val, isSubtotal: false, isCost: true, key: item.key };
  });

  const maxVal = Math.max(...data.map(d => d.base + d.value), 1);

  const barWidth = 52;
  const gap = 12;
  const leftPad = 90;
  const chartWidth = Math.max(data.length * (barWidth + gap) + leftPad + 20, 700);
  const chartHeight = 340;
  const plotTop = 24;
  const plotBottom = 50;
  const plotHeight = chartHeight - plotTop - plotBottom;

  const yScale = (v: number) => plotTop + plotHeight - (v / maxVal) * plotHeight;

  // Compact number formatter for Y axis
  const fmtAxis = (v: number) => {
    if (v >= 1e9) return `${(v / 1e9).toFixed(1)} Mrd`;
    if (v >= 1e6) return `${(v / 1e6).toFixed(0)} M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(0)} e`;
    return String(v);
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={chartWidth} height={chartHeight} style={{ display: 'block' }}>
        {/* Y axis grid */}
        {[0, 0.25, 0.5, 0.75, 1].map(pct => {
          const y = yScale(pct * maxVal);
          return (
            <g key={pct}>
              <line x1={leftPad - 4} y1={y} x2={chartWidth - 10} y2={y} stroke="#eee" strokeWidth={1} />
              <text x={leftPad - 8} y={y + 4} textAnchor="end" fontSize={10} fill="#aaa" fontFamily="system-ui">
                {fmtAxis(pct * maxVal)}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {data.map((d, i) => {
          const x = leftPad + i * (barWidth + gap);
          const barTop = yScale(d.base + d.value);
          const barBottom = yScale(d.base);
          const barH = Math.max(barBottom - barTop, 2);
          const fill = d.isCost ? '#94a3b8' : '#475569';

          // Connector from previous bar
          let connector = null;
          if (i > 0) {
            const prevD = data[i - 1];
            const prevX = leftPad + (i - 1) * (barWidth + gap);
            const connY = d.isCost
              ? yScale(d.base + d.value)     // top of cost = running before deduction
              : yScale(prevD.isSubtotal ? prevD.value : prevD.base); // from prev bottom

            // For subtotals after a cost, connect from prev cost bottom
            const fromY = prevD.isCost ? yScale(prevD.base) : yScale(prevD.value);

            connector = (
              <line
                x1={prevX + barWidth} y1={fromY}
                x2={x} y2={fromY}
                stroke="#d1d5db" strokeWidth={1} strokeDasharray="4,3"
              />
            );
          }

          return (
            <g key={d.key}>
              {connector}
              <rect x={x} y={barTop} width={barWidth} height={barH} rx={2} fill={fill} />
              {/* Value above bar */}
              <text
                x={x + barWidth / 2}
                y={barTop - 6}
                textAnchor="middle"
                fontSize={10}
                fontWeight={600}
                fill="#333"
                fontFamily="system-ui"
              >
                {fmtAxis(d.raw)}
              </text>
              {/* Label below */}
              <text
                x={x + barWidth / 2}
                y={chartHeight - plotBottom + 16}
                textAnchor="middle"
                fontSize={10}
                fontWeight={d.isSubtotal ? 700 : 400}
                fill={d.isSubtotal ? '#333' : '#777'}
                fontFamily="system-ui"
              >
                {d.name}
              </text>
            </g>
          );
        })}

        {/* Baseline */}
        <line x1={leftPad - 4} y1={yScale(0)} x2={chartWidth - 10} y2={yScale(0)} stroke="#ccc" strokeWidth={1} />
      </svg>
    </div>
  );
}

const MONTH_NAMES = ['Január', 'Február', 'Március', 'Április', 'Május', 'Június', 'Július', 'Augusztus', 'Szeptember', 'Október', 'November', 'December'];
const MONTH_SHORT = ['Jan', 'Feb', 'Márc', 'Ápr', 'Máj', 'Jún', 'Júl', 'Aug', 'Szept', 'Okt', 'Nov', 'Dec'];

function formatRangeSubtitle(from: string, to: string): string {
  if (from === to) return '';
  const [, mFrom] = from.split('-');
  const [, mTo] = to.split('-');
  return `${MONTH_SHORT[parseInt(mFrom, 10) - 1]} – ${MONTH_SHORT[parseInt(mTo, 10) - 1]}`;
}
const QUARTER_NAMES = ['Q1', 'Q2', 'Q3', 'Q4'];

interface PeriodGroup {
  label: string;
  from: string;
  to: string;
}

function groupPeriods(rawPeriods: string[], scale: 'month' | 'quarter' | 'year'): PeriodGroup[] {
  if (rawPeriods.length === 0) return [];

  if (scale === 'month') {
    return rawPeriods.map(p => {
      const [year, month] = p.split('-');
      const m = parseInt(month, 10);
      return { label: `${MONTH_NAMES[m - 1]}. ${year}`, from: p, to: p };
    });
  }

  if (scale === 'quarter') {
    const quarters = new Map<string, { from: string; to: string }>();
    for (const p of rawPeriods) {
      const [year, month] = p.split('-');
      const q = Math.ceil(parseInt(month, 10) / 3);
      const key = `${year}-Q${q}`;
      const existing = quarters.get(key);
      if (!existing) {
        quarters.set(key, { from: p, to: p });
      } else {
        if (p < existing.from) existing.from = p;
        if (p > existing.to) existing.to = p;
      }
    }
    return Array.from(quarters.entries()).map(([key, range]) => {
      const [year] = key.split('-Q');
      const q = parseInt(key.split('-Q')[1], 10);
      return { label: `${QUARTER_NAMES[q - 1]} ${year}`, from: range.from, to: range.to };
    });
  }

  // year
  const years = new Map<string, { from: string; to: string }>();
  for (const p of rawPeriods) {
    const year = p.split('-')[0];
    const existing = years.get(year);
    if (!existing) {
      years.set(year, { from: p, to: p });
    } else {
      if (p < existing.from) existing.from = p;
      if (p > existing.to) existing.to = p;
    }
  }
  return Array.from(years.entries()).map(([year, range]) => ({
    label: `${year}`, from: range.from, to: range.to,
  }));
}

const filterStyle: React.CSSProperties = {
  padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '8px',
  fontSize: '13px', background: '#fff', outline: 'none', color: '#333',
};

const miniInput: React.CSSProperties = {
  padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: '4px',
  fontSize: '11px', outline: 'none',
};

const toolBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '4px',
  padding: '8px 14px', border: '1px solid #d1d5db', borderRadius: '8px',
  background: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 500, color: '#555',
};

const labelStyle: React.CSSProperties = {
  fontSize: '11px', fontWeight: 600, color: '#555', display: 'block', marginBottom: '4px',
};

const modalCancelBtn: React.CSSProperties = {
  padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px',
  background: '#fff', cursor: 'pointer', fontSize: '12px',
};

const modalPrimaryBtn: React.CSSProperties = {
  padding: '8px 16px', border: 'none', borderRadius: '6px',
  background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
};

function bulkBtnStyle(bg: string): React.CSSProperties {
  return {
    display: 'flex', alignItems: 'center', gap: '4px',
    padding: '6px 14px', border: 'none', borderRadius: '6px',
    background: bg, color: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
  };
}
