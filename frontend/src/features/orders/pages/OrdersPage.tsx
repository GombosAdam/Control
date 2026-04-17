import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Plus, Package, Trash2, Check, XCircle, Clock, Circle, MessageSquare, X } from 'lucide-react';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { departmentsApi } from '../../../services/api/departments';
import { budgetApi } from '../../../services/api/budget';
import { useAuthStore } from '../../../stores/authStore';
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

const statusColors: Record<string, { bg: string; color: string }> = {
  draft: { bg: '#fef3c7', color: '#92400e' },
  approved: { bg: '#d1fae5', color: '#065f46' },
  received: { bg: '#dbeafe', color: '#1e40af' },
  closed: { bg: '#f3f4f6', color: '#374151' },
  cancelled: { bg: '#fecaca', color: '#991b1b' },
};

export function OrdersPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [items, setItems] = useState<PurchaseOrder[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [deptFilter, setDeptFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [approvalSteps, setApprovalSteps] = useState<ApprovalStep[]>([]);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [rejectStep, setRejectStep] = useState<ApprovalStep | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [receiveModal, setReceiveModal] = useState<string | null>(null);
  const [receiveDate, setReceiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [receiveNotes, setReceiveNotes] = useState('');
  const [budgetStatus, setBudgetStatus] = useState<any>(null);

  const load = () => {
    purchaseOrdersApi.list({
      page, limit: 50,
      department_id: deptFilter || undefined,
      status: statusFilter || undefined,
    }).then(data => { setItems(data.items); setTotal(data.total); });
  };

  useEffect(() => { departmentsApi.list().then(setDepartments); }, []);
  useEffect(() => { load(); }, [page, deptFilter, statusFilter]);

  useEffect(() => {
    if (!selectedId) { setApprovalSteps([]); setBudgetStatus(null); return; }
    purchaseOrdersApi.getApprovals(selectedId)
      .then(setApprovalSteps)
      .catch(() => setApprovalSteps([]));
    // Load budget status for the selected PO
    const po = items.find(i => i.id === selectedId);
    if (po?.budget_line_id) {
      budgetApi.getLineBudgetStatus(po.budget_line_id)
        .then(setBudgetStatus)
        .catch(() => setBudgetStatus(null));
    } else {
      setBudgetStatus(null);
    }
  }, [selectedId]);

  const handleReceive = async () => {
    if (!receiveModal) return;
    await purchaseOrdersApi.receive(receiveModal, { received_date: receiveDate, notes: receiveNotes || undefined });
    setReceiveModal(null);
    setReceiveDate(new Date().toISOString().slice(0, 10));
    setReceiveNotes('');
    load();
  };
  const handleDelete = async (id: string) => { if (confirm('Biztosan törli?')) { await purchaseOrdersApi.delete(id); load(); } };

  const handleApprovalDecision = async (step: ApprovalStep, decision: 'approved' | 'rejected', comment?: string) => {
    if (!selectedId) return;
    setApprovalLoading(true);
    try {
      await purchaseOrdersApi.decideApproval(selectedId, step.step, decision, comment);
      const data = await purchaseOrdersApi.getApprovals(selectedId);
      setApprovalSteps(data);
      load();
    } catch { }
    setApprovalLoading(false);
  };

  const handleReject = async () => {
    if (!rejectStep) return;
    await handleApprovalDecision(rejectStep, 'rejected', rejectComment || undefined);
    setRejectStep(null);
    setRejectComment('');
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      {/* Left panel - PO list */}
      <div style={{
        width: selectedId ? '55%' : '100%', minWidth: '600px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>
              {t('nav.orders')} <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total})</span>
            </h1>
            <button onClick={() => navigate('/orders/new')} style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px',
              background: '#06B6D4', color: '#fff', border: 'none', borderRadius: '6px',
              cursor: 'pointer', fontSize: '13px', fontWeight: 500,
            }}>
              <Plus size={14} /> {t('common.create')}
            </button>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            {(user?.role === 'admin' || user?.role === 'cfo' || user?.role === 'accountant') ? (
              <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)} style={selectStyle}>
                <option value="">{t('nav.departments')} - {t('invoices.all')}</option>
                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            ) : (
              <div style={{ ...selectStyle, background: '#f3f4f6', color: '#374151', display: 'flex', alignItems: 'center' }}>
                {departments.find(d => d.id === user?.department_id)?.name || 'Saját osztály'}
              </div>
            )}
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={selectStyle}>
              <option value="">{t('invoices.status')} - {t('invoices.all')}</option>
              {['draft', 'approved', 'received', 'closed', 'cancelled'].map(s =>
                <option key={s} value={s}>{s}</option>
              )}
            </select>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', background: '#fafafa' }}>
          {items.map(po => {
            const isSelected = selectedId === po.id;
            const sc = statusColors[po.status] || statusColors.draft;
            return (
              <div key={po.id} onClick={() => setSelectedId(isSelected ? null : po.id)} style={{
                padding: '12px 20px', borderBottom: '1px solid #f0f0f0', cursor: 'pointer',
                background: isSelected ? '#eff6ff' : '#fff',
                borderLeft: isSelected ? '3px solid #06B6D4' : '3px solid transparent',
              }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, fontSize: '13px', color: '#06B6D4' }}>{po.po_number}</span>
                      <span style={{ padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600, background: sc.bg, color: sc.color }}>
                        {po.status}
                      </span>
                      {po.goods_receipt && (
                        <span style={{ padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600, background: '#dbeafe', color: '#1e40af' }}>
                          {po.goods_receipt.gr_number}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                      {po.partner_name || po.supplier_name} {po.supplier_tax_id ? `(${po.supplier_tax_id})` : ''} · {po.department_name}
                    </div>
                    <div style={{ fontSize: '11px', color: '#999', marginTop: '1px' }}>
                      {po.accounting_code} · {po.budget_line_name || '-'} · {new Date(po.created_at).toLocaleDateString('hu')}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, fontSize: '14px' }}>{formatCurrency(po.amount, po.currency)}</div>
                    <div style={{ display: 'flex', gap: '4px', marginTop: '4px', justifyContent: 'flex-end' }} onClick={e => e.stopPropagation()}>
                      {po.status === 'approved' && (
                        <button onClick={() => setReceiveModal(po.id)} title="Átvétel" style={actionBtn}><Package size={12} /></button>
                      )}
                      {po.status === 'draft' && (
                        <button onClick={() => handleDelete(po.id)} title="Delete" style={actionBtn}><Trash2 size={12} /></button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
        </div>
      </div>

      {/* Right panel - Approval Timeline + Details */}
      {selectedId && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f3f4f6' }}>
          <div style={{
            padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#333' }}>
              {items.find(i => i.id === selectedId)?.po_number} — {t('po.approvalTimeline')}
            </span>
            <button onClick={() => setSelectedId(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#666' }}>
              <X size={18} />
            </button>
          </div>

          {/* Approval Steps */}
          <div style={{ padding: '24px', overflowY: 'auto' }}>
            {approvalSteps.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {approvalSteps.map((step, idx) => {
                  const statusIcon = step.status === 'approved'
                    ? <Check size={16} color="#fff" />
                    : step.status === 'rejected' || step.status === 'cancelled'
                    ? <XCircle size={16} color="#fff" />
                    : step.status === 'pending'
                    ? <Clock size={16} color="#fff" />
                    : <Circle size={16} color="#fff" />;
                  const statusBg = step.status === 'approved' ? '#10B981'
                    : step.status === 'rejected' || step.status === 'cancelled' ? '#EF4444'
                    : step.status === 'pending' ? '#F97316'
                    : '#9CA3AF';

                  return (
                    <div key={step.id} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                        <div style={{
                          width: '36px', height: '36px', borderRadius: '50%', background: statusBg,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                          {statusIcon}
                        </div>
                        {idx < approvalSteps.length - 1 && (
                          <div style={{ width: '2px', height: '40px', background: step.status === 'approved' ? '#10B981' : '#e5e7eb', marginTop: '4px' }} />
                        )}
                      </div>
                      <div style={{ flex: 1, background: '#fff', borderRadius: '8px', padding: '14px', border: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px', color: '#1a1a1a' }}>{step.step_name}</div>
                            <div style={{ fontSize: '12px', color: '#888', marginTop: '2px' }}>
                              {step.assignee_name
                                ? `Felelős: ${step.assignee_name}`
                                : `Szerepkör: ${step.assigned_role}`}
                            </div>
                          </div>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                            background: statusBg + '20', color: statusBg,
                          }}>
                            {step.status}
                          </span>
                        </div>
                        {step.decider_name && (
                          <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
                            {step.decider_name} · {step.decided_at ? formatDate(step.decided_at) : ''}
                          </div>
                        )}
                        {step.comment && (
                          <div style={{ fontSize: '12px', color: '#EF4444', marginTop: '4px', fontStyle: 'italic' }}>
                            "{step.comment}"
                          </div>
                        )}
                        {/* Decision buttons for pending step */}
                        {step.status === 'pending' && (
                          <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                            <button
                              onClick={() => handleApprovalDecision(step, 'approved')}
                              disabled={approvalLoading}
                              style={{
                                padding: '6px 16px', borderRadius: '6px', border: 'none',
                                background: '#10B981', color: '#fff', cursor: 'pointer',
                                fontSize: '12px', fontWeight: 600, opacity: approvalLoading ? 0.5 : 1,
                                display: 'flex', alignItems: 'center', gap: '6px',
                              }}
                            >
                              <Check size={14} /> {t('approvals.approve')}
                            </button>
                            <button
                              onClick={() => setRejectStep(step)}
                              disabled={approvalLoading}
                              style={{
                                padding: '6px 16px', borderRadius: '6px', border: 'none',
                                background: '#EF4444', color: '#fff', cursor: 'pointer',
                                fontSize: '12px', fontWeight: 600, opacity: approvalLoading ? 0.5 : 1,
                                display: 'flex', alignItems: 'center', gap: '6px',
                              }}
                            >
                              <XCircle size={14} /> {t('approvals.reject')}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
                {t('common.noData')}
              </div>
            )}

            {/* Budget keret info */}
            {budgetStatus && (() => {
              const po = items.find(i => i.id === selectedId);
              const poAmount = po?.amount || 0;
              const afterApproval = budgetStatus.available;
              const bl = budgetStatus.budget_line;
              return (
                <div style={{ marginTop: '24px', background: '#f0fdf4', borderRadius: '8px', padding: '16px', border: '1px solid #bbf7d0' }}>
                  <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#065f46', marginBottom: '10px', textTransform: 'uppercase' }}>Budget keret — {bl.account_code} {bl.account_name} ({bl.period})</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                    <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#666', fontWeight: 600 }}>TERVEZETT</div>
                      <div style={{ fontSize: '15px', fontWeight: 700 }}>{formatCurrency(bl.planned_amount, bl.currency)}</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#666', fontWeight: 600 }}>LEKÖTÖTT (PO)</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#F59E0B' }}>{formatCurrency(budgetStatus.committed, bl.currency)}</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '8px', background: '#fff', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#666', fontWeight: 600 }}>SZABAD KERET</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: afterApproval >= 0 ? '#10B981' : '#EF4444' }}>{formatCurrency(afterApproval, bl.currency)}</div>
                    </div>
                  </div>
                  {budgetStatus.purchase_orders.length > 1 && (
                    <details style={{ fontSize: '11px', color: '#555' }}>
                      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Összes PO ezen a budget soron ({budgetStatus.purchase_orders.length})</summary>
                      <div style={{ marginTop: '6px' }}>
                        {budgetStatus.purchase_orders.map((p: any) => (
                          <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', borderBottom: '1px solid #e5e7eb' }}>
                            <span><span style={{ color: '#06B6D4', fontWeight: 600 }}>{p.po_number}</span> {p.supplier_name} <span style={{ padding: '0 4px', borderRadius: '3px', fontSize: '9px', background: p.status === 'approved' ? '#d1fae5' : '#fef3c7', color: p.status === 'approved' ? '#065f46' : '#92400e' }}>{p.status}</span></span>
                            <span style={{ fontWeight: 600 }}>{formatCurrency(p.amount, p.currency)}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              );
            })()}

            {/* PO Details */}
            {(() => {
              const po = items.find(i => i.id === selectedId);
              if (!po) return null;
              return (
                <>
                  <div style={{ marginTop: '24px', background: '#fff', borderRadius: '8px', padding: '16px', border: '1px solid #e5e7eb' }}>
                    <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#666', marginBottom: '12px', textTransform: 'uppercase' }}>PO részletek</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                      <div><span style={{ color: '#888' }}>Szállító:</span> {po.supplier_name}</div>
                      <div><span style={{ color: '#888' }}>Adószám:</span> {po.supplier_tax_id || '-'}</div>
                      <div><span style={{ color: '#888' }}>Összeg:</span> <strong>{formatCurrency(po.amount, po.currency)}</strong></div>
                      <div><span style={{ color: '#888' }}>Számla kód:</span> <code>{po.accounting_code}</code></div>
                      <div><span style={{ color: '#888' }}>Osztály:</span> {po.department_name}</div>
                      <div><span style={{ color: '#888' }}>Budget sor:</span> {po.budget_line_name || '-'}</div>
                    </div>
                    {po.amount >= 500000 && (
                      <div style={{ marginTop: '10px', padding: '6px 10px', background: '#fef3c7', borderRadius: '6px', fontSize: '11px', color: '#92400e' }}>
                        {t('po.threshold')}
                      </div>
                    )}
                  </div>

                  {/* PO Line Items */}
                  {po.lines && po.lines.length > 0 && (
                    <div style={{ marginTop: '16px', background: '#fff', borderRadius: '8px', padding: '16px', border: '1px solid #e5e7eb' }}>
                      <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#666', marginBottom: '12px', textTransform: 'uppercase' }}>Tételsorok</h3>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                            <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600 }}>Leírás</th>
                            <th style={{ padding: '4px 8px', textAlign: 'right', color: '#888', fontWeight: 600 }}>Menny.</th>
                            <th style={{ padding: '4px 8px', textAlign: 'right', color: '#888', fontWeight: 600 }}>Egységár</th>
                            <th style={{ padding: '4px 8px', textAlign: 'right', color: '#888', fontWeight: 600 }}>Nettó</th>
                          </tr>
                        </thead>
                        <tbody>
                          {po.lines.map(line => (
                            <tr key={line.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                              <td style={{ padding: '4px 8px' }}>{line.description}</td>
                              <td style={{ padding: '4px 8px', textAlign: 'right' }}>{line.quantity}</td>
                              <td style={{ padding: '4px 8px', textAlign: 'right' }}>{formatCurrency(line.unit_price, po.currency)}</td>
                              <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(line.net_amount, po.currency)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Goods Receipt info */}
                  {po.goods_receipt && (
                    <div style={{ marginTop: '16px', background: '#eff6ff', borderRadius: '8px', padding: '14px', border: '1px solid #bfdbfe' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: '#1e40af' }}>
                        <Check size={16} /> Átvéve: {po.goods_receipt.gr_number}
                      </div>
                      <div style={{ fontSize: '12px', color: '#3b82f6', marginTop: '4px' }}>
                        {po.goods_receipt.received_date} | {po.goods_receipt.receiver_name || '-'}
                        {po.goods_receipt.notes && <span> | {po.goods_receipt.notes}</span>}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        </div>
      )}

      {/* Reject modal */}
      {rejectStep && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => { setRejectStep(null); setRejectComment(''); }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '400px', maxWidth: '90vw' }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 600 }}>PO elutasítása</h3>
            <p style={{ margin: '0 0 16px', fontSize: '13px', color: '#666' }}>{rejectStep.step_name}</p>
            <textarea value={rejectComment} onChange={e => setRejectComment(e.target.value)}
              placeholder={t('approvals.commentPlaceholder')}
              style={{
                width: '100%', minHeight: '80px', padding: '10px', borderRadius: '6px',
                border: '1px solid #d1d5db', fontSize: '13px', resize: 'vertical', boxSizing: 'border-box',
              }} />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button onClick={() => { setRejectStep(null); setRejectComment(''); }}
                style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer', fontSize: '13px' }}>
                {t('common.cancel')}
              </button>
              <button onClick={handleReject} disabled={approvalLoading}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: 'none',
                  background: '#EF4444', color: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
                  display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                <MessageSquare size={14} /> {t('approvals.confirmReject')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Receive modal */}
      {receiveModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', zIndex: 300,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => { setReceiveModal(null); setReceiveNotes(''); }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '420px', maxWidth: '90vw' }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 600 }}>Áruátvétel</h3>
            <p style={{ margin: '0 0 16px', fontSize: '13px', color: '#666' }}>
              {items.find(i => i.id === receiveModal)?.po_number} — {items.find(i => i.id === receiveModal)?.supplier_name}
            </p>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#555', marginBottom: '4px' }}>Átvétel dátuma</label>
              <input type="date" value={receiveDate} onChange={e => setReceiveDate(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', boxSizing: 'border-box' }} />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#555', marginBottom: '4px' }}>Megjegyzés (opcionális)</label>
              <textarea value={receiveNotes} onChange={e => setReceiveNotes(e.target.value)}
                placeholder="Átvételi megjegyzés..."
                style={{
                  width: '100%', minHeight: '60px', padding: '10px', borderRadius: '6px',
                  border: '1px solid #d1d5db', fontSize: '13px', resize: 'vertical', boxSizing: 'border-box',
                }} />
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button onClick={() => { setReceiveModal(null); setReceiveNotes(''); }}
                style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer', fontSize: '13px' }}>
                {t('common.cancel')}
              </button>
              <button onClick={handleReceive}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: 'none',
                  background: '#06B6D4', color: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
                  display: 'flex', alignItems: 'center', gap: '6px',
                }}>
                <Package size={14} /> Átveszem
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const selectStyle: React.CSSProperties = { padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', background: '#fff' };
const actionBtn: React.CSSProperties = { padding: '4px 8px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center' };
