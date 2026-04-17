import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, XCircle, Clock, Circle, ChevronDown, ChevronRight, RefreshCw } from 'lucide-react';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { departmentsApi } from '../../../services/api/departments';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import type { PurchaseOrder, Department } from '../../../types/controlling';

interface ApprovalStep {
  id: string;
  step: number;
  step_name: string;
  status: string;
  assigned_role: string;
  assigned_to: string | null;
  assignee_name: string | null;
  decided_by: string | null;
  decider_name: string | null;
  decided_at: string | null;
  comment: string | null;
  created_at: string;
}

interface POWithApprovals {
  po: PurchaseOrder;
  steps: ApprovalStep[];
  loading: boolean;
}

const poStatusColors: Record<string, { bg: string; color: string }> = {
  draft: { bg: '#fef3c7', color: '#92400e' },
  pending_approval: { bg: '#fef3c7', color: '#92400e' },
  approved: { bg: '#d1fae5', color: '#065f46' },
  sent: { bg: '#e0e7ff', color: '#3730a3' },
  received: { bg: '#dbeafe', color: '#1e40af' },
  closed: { bg: '#f3f4f6', color: '#374151' },
  cancelled: { bg: '#fecaca', color: '#991b1b' },
};

const stepStatusColors: Record<string, { bg: string; color: string; icon: typeof Check }> = {
  approved: { bg: '#10B981', color: '#fff', icon: Check },
  rejected: { bg: '#EF4444', color: '#fff', icon: XCircle },
  cancelled: { bg: '#EF4444', color: '#fff', icon: XCircle },
  pending: { bg: '#F97316', color: '#fff', icon: Clock },
  waiting: { bg: '#9CA3AF', color: '#fff', icon: Circle },
};

export function POApprovalsPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<PurchaseOrder[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [deptFilter, setDeptFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [approvalCache, setApprovalCache] = useState<Record<string, { steps: ApprovalStep[]; loading: boolean }>>({});
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const data = await purchaseOrdersApi.list({
        page, limit: 50,
        department_id: deptFilter || undefined,
        status: statusFilter || undefined,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch {
      setItems([]);
      setTotal(0);
    }
  };

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);
  useEffect(() => { load(); }, [page, deptFilter, statusFilter]);

  const toggleExpand = async (poId: string) => {
    const next = new Set(expandedIds);
    if (next.has(poId)) {
      next.delete(poId);
    } else {
      next.add(poId);
      // Load approvals if not cached
      if (!approvalCache[poId]) {
        setApprovalCache(prev => ({ ...prev, [poId]: { steps: [], loading: true } }));
        try {
          const steps = await purchaseOrdersApi.getApprovals(poId);
          setApprovalCache(prev => ({ ...prev, [poId]: { steps, loading: false } }));
        } catch {
          setApprovalCache(prev => ({ ...prev, [poId]: { steps: [], loading: false } }));
        }
      }
    }
    setExpandedIds(next);
  };

  const expandAll = async () => {
    const allIds = new Set(items.map(i => i.id));
    setExpandedIds(allIds);
    // Load all approvals
    for (const po of items) {
      if (!approvalCache[po.id]) {
        setApprovalCache(prev => ({ ...prev, [po.id]: { steps: [], loading: true } }));
        purchaseOrdersApi.getApprovals(po.id).then(steps => {
          setApprovalCache(prev => ({ ...prev, [po.id]: { steps, loading: false } }));
        }).catch(() => {
          setApprovalCache(prev => ({ ...prev, [po.id]: { steps: [], loading: false } }));
        });
      }
    }
  };

  const collapseAll = () => {
    setExpandedIds(new Set());
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setApprovalCache({});
    await load();
    // Reload approvals for expanded items
    for (const poId of expandedIds) {
      purchaseOrdersApi.getApprovals(poId).then(steps => {
        setApprovalCache(prev => ({ ...prev, [poId]: { steps, loading: false } }));
      }).catch(() => {
        setApprovalCache(prev => ({ ...prev, [poId]: { steps: [], loading: false } }));
      });
    }
    setRefreshing(false);
  };

  const getApprovalSummary = (steps: ApprovalStep[]): { current: number; total: number; status: string } => {
    if (steps.length === 0) return { current: 0, total: 0, status: 'unknown' };
    const approved = steps.filter(s => s.status === 'approved').length;
    const rejected = steps.some(s => s.status === 'rejected');
    const pending = steps.find(s => s.status === 'pending');
    if (rejected) return { current: approved, total: steps.length, status: 'rejected' };
    if (approved === steps.length) return { current: steps.length, total: steps.length, status: 'completed' };
    return { current: approved, total: steps.length, status: pending ? 'in_progress' : 'waiting' };
  };

  const pages = Math.ceil(total / 50) || 1;

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>
            {t('admin.poApprovals')}
            <span style={{ fontSize: '13px', color: '#999', fontWeight: 400, marginLeft: '8px' }}>({total})</span>
          </h1>
          <p style={{ fontSize: '13px', color: '#888', margin: '4px 0 0' }}>
            {t('admin.poApprovalsDesc')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={expandAll} style={headerBtn}>
            <ChevronDown size={14} /> {t('admin.expandAll')}
          </button>
          <button onClick={collapseAll} style={headerBtn}>
            <ChevronRight size={14} /> {t('admin.collapseAll')}
          </button>
          <button onClick={handleRefresh} disabled={refreshing} style={{ ...headerBtn, background: '#06B6D4', color: '#fff', border: 'none' }}>
            <RefreshCw size={14} style={refreshing ? { animation: 'spin 0.8s linear infinite' } : {}} /> {t('common.refresh')}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <select value={deptFilter} onChange={e => { setDeptFilter(e.target.value); setPage(1); }} style={selectStyle}>
          <option value="">{t('nav.departments')} - {t('invoices.all')}</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} style={selectStyle}>
          <option value="">{t('invoices.status')} - {t('invoices.all')}</option>
          {['draft', 'pending_approval', 'approved', 'sent', 'received', 'closed', 'cancelled'].map(s =>
            <option key={s} value={s}>{s}</option>
          )}
        </select>
      </div>

      {/* Table */}
      <div style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', overflow: 'hidden' }}>
        {/* Table header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '32px 120px 1fr 160px 120px 140px 200px',
          padding: '10px 16px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb',
          fontSize: '11px', fontWeight: 600, color: '#888', textTransform: 'uppercase',
        }}>
          <div></div>
          <div>PO#</div>
          <div>{t('invoices.partner')}</div>
          <div>{t('nav.departments')}</div>
          <div style={{ textAlign: 'right' }}>{t('invoices.amount')}</div>
          <div style={{ textAlign: 'center' }}>{t('invoices.status')}</div>
          <div style={{ textAlign: 'center' }}>{t('admin.approvalProgress')}</div>
        </div>

        {/* Rows */}
        {items.map(po => {
          const isExpanded = expandedIds.has(po.id);
          const cache = approvalCache[po.id];
          const sc = poStatusColors[po.status] || poStatusColors.draft;

          return (
            <div key={po.id}>
              {/* PO row */}
              <div
                onClick={() => toggleExpand(po.id)}
                style={{
                  display: 'grid', gridTemplateColumns: '32px 120px 1fr 160px 120px 140px 200px',
                  padding: '12px 16px', borderBottom: '1px solid #f0f0f0', cursor: 'pointer',
                  background: isExpanded ? '#f0f7ff' : '#fff',
                  alignItems: 'center',
                }}
                onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = isExpanded ? '#f0f7ff' : '#fff'; }}
              >
                <div style={{ color: '#888' }}>
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
                <div style={{ fontWeight: 600, fontSize: '13px', color: '#06B6D4' }}>{po.po_number}</div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 500 }}>{po.supplier_name}</div>
                  <div style={{ fontSize: '11px', color: '#999' }}>{po.accounting_code} · {formatDate(po.created_at)}</div>
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>{po.department_name}</div>
                <div style={{ textAlign: 'right', fontWeight: 700, fontSize: '13px' }}>{formatCurrency(po.amount, po.currency)}</div>
                <div style={{ textAlign: 'center' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                    background: sc.bg, color: sc.color,
                  }}>
                    {po.status}
                  </span>
                </div>
                <div style={{ textAlign: 'center' }}>
                  {cache && !cache.loading && cache.steps.length > 0 ? (
                    <ApprovalProgressBar steps={cache.steps} />
                  ) : cache?.loading ? (
                    <span style={{ fontSize: '11px', color: '#999' }}>...</span>
                  ) : (
                    <span style={{ fontSize: '11px', color: '#ccc' }}>-</span>
                  )}
                </div>
              </div>

              {/* Expanded approval chain */}
              {isExpanded && (
                <div style={{ padding: '16px 16px 16px 48px', background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
                  {cache?.loading ? (
                    <div style={{ fontSize: '12px', color: '#999' }}>{t('common.loading')}</div>
                  ) : cache?.steps && cache.steps.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: '#666', marginBottom: '4px', textTransform: 'uppercase' }}>
                        {t('po.approvalTimeline')} ({cache.steps.length} {t('approvals.step').toLowerCase()})
                      </div>
                      {cache.steps.map((step, idx) => {
                        const sc = stepStatusColors[step.status] || stepStatusColors.waiting;
                        const Icon = sc.icon;
                        return (
                          <div key={step.id} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                            {/* Timeline dot + line */}
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                              <div style={{
                                width: '28px', height: '28px', borderRadius: '50%', background: sc.bg,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                              }}>
                                <Icon size={14} color={sc.color} />
                              </div>
                              {idx < cache.steps.length - 1 && (
                                <div style={{
                                  width: '2px', height: '20px',
                                  background: step.status === 'approved' ? '#10B981' : '#e5e7eb',
                                  marginTop: '2px',
                                }} />
                              )}
                            </div>

                            {/* Step info */}
                            <div style={{
                              flex: 1, background: '#fff', borderRadius: '6px', padding: '10px 14px',
                              border: `1px solid ${step.status === 'pending' ? '#F97316' : '#e5e7eb'}`,
                              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                              minHeight: '28px',
                            }}>
                              <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{ fontWeight: 600, fontSize: '13px', color: '#1a1a1a' }}>
                                    {step.step}. {step.step_name}
                                  </span>
                                  <span style={{
                                    padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                                    background: sc.bg + '20', color: sc.bg,
                                  }}>
                                    {step.status}
                                  </span>
                                </div>
                                <div style={{ fontSize: '11px', color: '#888', marginTop: '2px' }}>
                                  {step.assignee_name
                                    ? `${step.assignee_name}`
                                    : `${step.assigned_role}`}
                                  {step.decider_name && (
                                    <span style={{ color: '#666' }}>
                                      {' '}· {step.status === 'approved' ? 'Jóváhagyta' : 'Elutasította'}: {step.decider_name}
                                    </span>
                                  )}
                                  {step.decided_at && (
                                    <span style={{ color: '#aaa' }}> · {formatDate(step.decided_at)}</span>
                                  )}
                                </div>
                                {step.comment && (
                                  <div style={{ fontSize: '11px', color: '#EF4444', marginTop: '3px', fontStyle: 'italic' }}>
                                    "{step.comment}"
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ fontSize: '12px', color: '#999' }}>{t('common.noData')}</div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {items.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '16px' }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={paginationBtn}>
            {t('common.previous')}
          </button>
          <span style={{ padding: '6px 12px', fontSize: '13px', color: '#666' }}>
            {page} / {pages}
          </span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} style={paginationBtn}>
            {t('common.next')}
          </button>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

/** Mini progress bar showing approval chain status */
function ApprovalProgressBar({ steps }: { steps: ApprovalStep[] }) {
  const total = steps.length;
  if (total === 0) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '3px', justifyContent: 'center' }}>
      {steps.map(step => {
        const bg = step.status === 'approved' ? '#10B981'
          : step.status === 'rejected' || step.status === 'cancelled' ? '#EF4444'
          : step.status === 'pending' ? '#F97316'
          : '#D1D5DB';
        return (
          <div
            key={step.id}
            title={`${step.step_name}: ${step.status}`}
            style={{
              width: `${Math.max(20, 120 / total)}px`,
              height: '8px',
              borderRadius: '4px',
              background: bg,
            }}
          />
        );
      })}
      <span style={{ fontSize: '10px', color: '#888', marginLeft: '4px' }}>
        {steps.filter(s => s.status === 'approved').length}/{total}
      </span>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', background: '#fff',
};

const headerBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px',
  background: '#f3f4f6', color: '#333', border: '1px solid #d1d5db', borderRadius: '6px',
  cursor: 'pointer', fontSize: '13px', fontWeight: 500,
};

const paginationBtn: React.CSSProperties = {
  padding: '6px 14px', borderRadius: '6px', border: '1px solid #d1d5db',
  background: '#fff', cursor: 'pointer', fontSize: '13px',
};
