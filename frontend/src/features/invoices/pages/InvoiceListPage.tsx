import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Upload, FileText, X, Play, Zap, Loader2, Send, Check, XCircle, Clock, Circle, MessageSquare } from 'lucide-react';
import { invoicesApi } from '../../../services/api/invoices';
import { useAuthStore } from '../../../stores/authStore';
import { formatDate } from '../../../utils/formatters';
import type { Invoice, InvoiceApprovalStep } from '../../../types/invoice';

const statusColors: Record<string, { bg: string; text: string }> = {
  uploaded: { bg: '#e0e7ff', text: '#4338ca' },
  ocr_processing: { bg: '#fef3c7', text: '#92400e' },
  ocr_done: { bg: '#dbeafe', text: '#1e40af' },
  extracting: { bg: '#fef3c7', text: '#92400e' },
  pending_review: { bg: '#fff7ed', text: '#c2410c' },
  in_approval: { bg: '#fff7ed', text: '#c2410c' },
  approved: { bg: '#d1fae5', text: '#059669' },
  awaiting_match: { bg: '#fef9c3', text: '#854d0e' },
  matched: { bg: '#dbeafe', text: '#1e40af' },
  posted: { bg: '#dcfce7', text: '#166534' },
  rejected: { bg: '#fee2e2', text: '#dc2626' },
  error: { bg: '#fee2e2', text: '#dc2626' },
};

export function InvoiceListPage() {
  const { t } = useTranslation();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [processAllRunning, setProcessAllRunning] = useState(false);
  const [submittingIds, setSubmittingIds] = useState<Set<string>>(new Set());
  const [approvalSteps, setApprovalSteps] = useState<InvoiceApprovalStep[]>([]);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [rejectStep, setRejectStep] = useState<InvoiceApprovalStep | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [approvalActionLoading, setApprovalActionLoading] = useState(false);
  const { user } = useAuthStore();

  const load = () => {
    invoicesApi.list({ page, limit: 50 })
      .then(data => { setInvoices(data.items); setTotal(data.total); });
  };

  useEffect(() => { load(); }, [page]);

  // Auto-refresh while processing
  useEffect(() => {
    if (processingIds.size > 0 || processAllRunning) {
      const interval = setInterval(load, 5000);
      return () => clearInterval(interval);
    }
  }, [processingIds.size, processAllRunning]);

  useEffect(() => {
    if (!selectedId) {
      if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }
      setApprovalSteps([]);
      return;
    }
    invoicesApi.getPdf(selectedId).then(blob => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
    });
    // Load approval steps
    setApprovalLoading(true);
    invoicesApi.getApprovals(selectedId)
      .then(data => setApprovalSteps(data))
      .catch(() => setApprovalSteps([]))
      .finally(() => setApprovalLoading(false));
  }, [selectedId]);

  const handleProcess = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setProcessingIds(prev => new Set(prev).add(id));
    try {
      await invoicesApi.reprocess(id);
    } catch { }
  };

  const handleProcessAll = async () => {
    setProcessAllRunning(true);
    try {
      const result = await invoicesApi.processAll();
      // Mark all uploaded as processing in UI
      const uploadedIds = invoices.filter(i => i.status === 'uploaded').map(i => i.id);
      setProcessingIds(new Set(uploadedIds));
    } catch { }
    setTimeout(() => setProcessAllRunning(false), 2000);
  };

  const handleSubmitForApproval = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSubmittingIds(prev => new Set(prev).add(id));
    try {
      await invoicesApi.submitForApproval(id);
      load();
    } catch { }
    setSubmittingIds(prev => { const s = new Set(prev); s.delete(id); return s; });
  };

  const handleApprovalDecision = async (step: InvoiceApprovalStep, decision: 'approved' | 'rejected', comment?: string) => {
    if (!selectedId) return;
    setApprovalActionLoading(true);
    try {
      await invoicesApi.decideApproval(selectedId, step.step, decision, comment);
      // Reload approval steps and invoice list
      const data = await invoicesApi.getApprovals(selectedId);
      setApprovalSteps(data);
      load();
    } catch { }
    setApprovalActionLoading(false);
  };

  const handleRejectApproval = async () => {
    if (!rejectStep) return;
    await handleApprovalDecision(rejectStep, 'rejected', rejectComment || undefined);
    setRejectStep(null);
    setRejectComment('');
  };

  const uploadedCount = invoices.filter(i => i.status === 'uploaded').length;

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      {/* Left panel - invoice list */}
      <div style={{
        width: selectedId ? '400px' : '100%',
        minWidth: '400px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #e5e7eb',
          background: '#fff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: uploadedCount > 0 ? '12px' : 0 }}>
            <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#1a1a1a', margin: 0 }}>
              {t('invoices.title')} <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total})</span>
            </h1>
            <Link to="/invoices/upload" style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px',
              background: '#10B981', color: '#fff', borderRadius: '6px', textDecoration: 'none',
              fontSize: '13px', fontWeight: 500,
            }}>
              <Upload size={14} /> {t('invoices.upload')}
            </Link>
          </div>

          {/* Process All button */}
          {uploadedCount > 0 && (
            <button
              onClick={handleProcessAll}
              disabled={processAllRunning}
              style={{
                width: '100%', padding: '10px', borderRadius: '8px', border: 'none',
                background: processAllRunning
                  ? '#f3f4f6'
                  : 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                color: processAllRunning ? '#999' : '#fff',
                fontSize: '13px', fontWeight: 600, cursor: processAllRunning ? 'default' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                boxShadow: processAllRunning ? 'none' : '0 2px 10px rgba(139,92,246,0.3)',
              }}
            >
              {processAllRunning ? (
                <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Feldolgozás indítva...</>
              ) : (
                <><Zap size={14} /> Összes feldolgozása ({uploadedCount} számla)</>
              )}
            </button>
          )}
        </div>

        {/* Invoice list */}
        <div style={{ flex: 1, overflowY: 'auto', background: '#fafafa' }}>
          {invoices.map(inv => {
            const isSelected = selectedId === inv.id;
            const isProcessing = processingIds.has(inv.id) || inv.status === 'ocr_processing' || inv.status === 'extracting';
            const sc = statusColors[inv.status] || statusColors.uploaded;

            return (
              <div
                key={inv.id}
                onClick={() => setSelectedId(isSelected ? null : inv.id)}
                style={{
                  padding: '10px 20px',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                  background: isSelected ? '#eff6ff' : '#fff',
                  borderLeft: isSelected ? '3px solid #3B82F6' : '3px solid transparent',
                }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileText size={16} color={isSelected ? '#3B82F6' : '#999'} strokeWidth={1.5} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <p style={{
                        margin: 0, fontSize: '13px', fontWeight: 500, color: '#1a1a1a',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                      }}>
                        {inv.original_filename}
                      </p>
                      <span style={{
                        padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                        background: sc.bg, color: sc.text, whiteSpace: 'nowrap', flexShrink: 0,
                      }}>
                        {isProcessing ? '⏳' : ''} {t(`status.${inv.status}`)}
                      </span>
                    </div>
                    <p style={{ margin: '2px 0 0', fontSize: '11px', color: '#999' }}>
                      {formatDate(inv.created_at)}
                    </p>
                  </div>

                  {/* Process button for uploaded invoices */}
                  {inv.status === 'uploaded' && !processingIds.has(inv.id) && (
                    <button
                      onClick={(e) => handleProcess(inv.id, e)}
                      title="Feldolgozás"
                      style={{
                        padding: '4px 8px', borderRadius: '4px', border: 'none',
                        background: '#0EA5E9', color: '#fff', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: '4px',
                        fontSize: '11px', fontWeight: 500, flexShrink: 0,
                      }}
                    >
                      <Play size={10} fill="#fff" /> AI
                    </button>
                  )}

                  {/* Submit for approval button */}
                  {inv.status === 'pending_review' && !submittingIds.has(inv.id) && (
                    <button
                      onClick={(e) => handleSubmitForApproval(inv.id, e)}
                      title={t('approvals.submitForApproval', 'Jóváhagyásra küldés')}
                      style={{
                        padding: '4px 8px', borderRadius: '4px', border: 'none',
                        background: '#F97316', color: '#fff', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: '4px',
                        fontSize: '11px', fontWeight: 500, flexShrink: 0,
                      }}
                    >
                      <Send size={10} /> {t('approvals.submit', 'Jóváhagyás')}
                    </button>
                  )}
                  {submittingIds.has(inv.id) && (
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite', color: '#F97316', flexShrink: 0 }} />
                  )}
                </div>
              </div>
            );
          })}
          {invoices.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('invoices.noInvoices')}</div>
          )}
        </div>

        {/* Pagination */}
        {total > 50 && (
          <div style={{
            padding: '8px 20px', borderTop: '1px solid #e5e7eb', background: '#fff',
            display: 'flex', justifyContent: 'center', gap: '8px', alignItems: 'center',
          }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              style={{
                padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: '4px',
                background: '#fff', cursor: page === 1 ? 'default' : 'pointer', fontSize: '13px',
                opacity: page === 1 ? 0.5 : 1,
              }}>
              {t('common.previous')}
            </button>
            <span style={{ fontSize: '13px', color: '#666' }}>{page} / {Math.ceil(total / 50)}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 50)}
              style={{
                padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: '4px',
                background: '#fff', cursor: page >= Math.ceil(total / 50) ? 'default' : 'pointer', fontSize: '13px',
                opacity: page >= Math.ceil(total / 50) ? 0.5 : 1,
              }}>
              {t('common.next')}
            </button>
          </div>
        )}
      </div>

      {/* Right panel - PDF viewer */}
      {selectedId && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f3f4f6' }}>
          <div style={{
            padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#333' }}>
              {invoices.find(i => i.id === selectedId)?.original_filename}
            </span>
            <button
              onClick={() => setSelectedId(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#666' }}
            >
              <X size={18} />
            </button>
          </div>
          {/* Approval Timeline */}
          {approvalSteps.length > 0 && (
            <div style={{
              padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb',
            }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
                {t('approvals.timeline', 'Jóváhagyási folyamat')}
              </div>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-start' }}>
                {approvalSteps.map((step, idx) => {
                  const statusIcon = step.status === 'approved'
                    ? <Check size={14} color="#fff" />
                    : step.status === 'rejected'
                    ? <XCircle size={14} color="#fff" />
                    : step.status === 'pending'
                    ? <Clock size={14} color="#fff" />
                    : <Circle size={14} color="#fff" />;
                  const statusBg = step.status === 'approved' ? '#10B981'
                    : step.status === 'rejected' ? '#EF4444'
                    : step.status === 'pending' ? '#F97316'
                    : '#9CA3AF';

                  return (
                    <div key={step.id} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        {idx > 0 && <div style={{ flex: 1, height: '2px', background: idx > 0 && approvalSteps[idx - 1].status === 'approved' ? '#10B981' : '#e5e7eb' }} />}
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '50%', background: statusBg,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                          {statusIcon}
                        </div>
                        {idx < approvalSteps.length - 1 && <div style={{ flex: 1, height: '2px', background: step.status === 'approved' ? '#10B981' : '#e5e7eb' }} />}
                      </div>
                      <span style={{ fontSize: '10px', color: '#666', marginTop: '4px', textAlign: 'center' }}>
                        {step.step_name}
                      </span>
                      {step.decider_name && (
                        <span style={{ fontSize: '9px', color: '#999', textAlign: 'center' }}>
                          {step.decider_name}
                        </span>
                      )}
                      {step.decided_at && (
                        <span style={{ fontSize: '9px', color: '#999', textAlign: 'center' }}>
                          {formatDate(step.decided_at)}
                        </span>
                      )}
                      {step.comment && (
                        <span style={{ fontSize: '9px', color: '#EF4444', textAlign: 'center', fontStyle: 'italic' }}>
                          "{step.comment}"
                        </span>
                      )}
                      {/* Decision buttons for pending step */}
                      {step.status === 'pending' && (
                        <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                          <button
                            onClick={() => handleApprovalDecision(step, 'approved')}
                            disabled={approvalActionLoading}
                            style={{
                              padding: '2px 8px', borderRadius: '4px', border: 'none',
                              background: '#10B981', color: '#fff', cursor: 'pointer',
                              fontSize: '10px', fontWeight: 500, opacity: approvalActionLoading ? 0.5 : 1,
                            }}
                          >
                            {t('approvals.approve', 'Jóváhagyom')}
                          </button>
                          <button
                            onClick={() => setRejectStep(step)}
                            disabled={approvalActionLoading}
                            style={{
                              padding: '2px 8px', borderRadius: '4px', border: 'none',
                              background: '#EF4444', color: '#fff', cursor: 'pointer',
                              fontSize: '10px', fontWeight: 500, opacity: approvalActionLoading ? 0.5 : 1,
                            }}
                          >
                            {t('approvals.reject', 'Elutasítom')}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ flex: 1 }}>
            {pdfUrl ? (
              <iframe src={pdfUrl} style={{ width: '100%', height: '100%', border: 'none' }} title="PDF Preview" />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
                {t('common.loading')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reject modal for approval timeline */}
      {rejectStep && (
        <div
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 300,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          onClick={() => { setRejectStep(null); setRejectComment(''); }}
        >
          <div
            style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '400px', maxWidth: '90vw' }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 600 }}>
              {t('approvals.rejectTitle', 'Számla elutasítása')}
            </h3>
            <p style={{ margin: '0 0 16px', fontSize: '13px', color: '#666' }}>
              {rejectStep.step_name}
            </p>
            <textarea
              value={rejectComment}
              onChange={e => setRejectComment(e.target.value)}
              placeholder={t('approvals.commentPlaceholder', 'Elutasítás indoka...')}
              style={{
                width: '100%', minHeight: '80px', padding: '10px', borderRadius: '6px',
                border: '1px solid #d1d5db', fontSize: '13px', resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                onClick={() => { setRejectStep(null); setRejectComment(''); }}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: '1px solid #d1d5db',
                  background: '#fff', cursor: 'pointer', fontSize: '13px',
                }}
              >
                {t('common.cancel', 'Mégse')}
              </button>
              <button
                onClick={handleRejectApproval}
                disabled={approvalActionLoading}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: 'none',
                  background: '#EF4444', color: '#fff', cursor: 'pointer',
                  fontSize: '13px', fontWeight: 500, opacity: approvalActionLoading ? 0.5 : 1,
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <MessageSquare size={14} /> {t('approvals.confirmReject', 'Elutasítás')}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
