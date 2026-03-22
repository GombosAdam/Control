import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, XCircle, X, FileText, Check, Clock, Circle, MessageSquare } from 'lucide-react';
import { extractionApi } from '../../../services/api/extraction';
import { invoicesApi } from '../../../services/api/invoices';
import { formatCurrency, formatDate } from '../../../utils/formatters';
import type { InvoiceApprovalStep } from '../../../types/invoice';

const statusColors: Record<string, { bg: string; text: string; label: string }> = {
  pending_review: { bg: '#fff7ed', text: '#c2410c', label: 'Kinyerve' },
  in_approval: { bg: '#eff6ff', text: '#1d4ed8', label: 'Jóváhagyás alatt' },
  approved: { bg: '#d1fae5', text: '#059669', label: 'Jóváhagyva' },
};

export function ExtractionQueuePage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [approvalSteps, setApprovalSteps] = useState<InvoiceApprovalStep[]>([]);
  const [approvalActionLoading, setApprovalActionLoading] = useState(false);
  const [rejectStep, setRejectStep] = useState<InvoiceApprovalStep | null>(null);
  const [rejectComment, setRejectComment] = useState('');

  const load = () => { extractionApi.getQueue({ limit: 50 }).then(data => setItems(data.items)); };
  useEffect(() => { load(); }, []);

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
    invoicesApi.getApprovals(selectedId)
      .then(data => setApprovalSteps(data))
      .catch(() => setApprovalSteps([]));
  }, [selectedId]);

  const handleApprove = async (id: string) => {
    await extractionApi.approve(id);
    if (selectedId === id) {
      // Reload approval steps for newly approved extraction
      invoicesApi.getApprovals(id)
        .then(data => setApprovalSteps(data))
        .catch(() => setApprovalSteps([]));
    }
    load();
  };

  const handleReject = async (id: string) => {
    await extractionApi.reject(id);
    if (selectedId === id) setSelectedId(null);
    load();
  };

  const handleApprovalDecision = async (step: InvoiceApprovalStep, decision: 'approved' | 'rejected', comment?: string) => {
    if (!selectedId) return;
    setApprovalActionLoading(true);
    try {
      await invoicesApi.decideApproval(selectedId, step.step, decision, comment);
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

  const selected = items.find(i => i.id === selectedId);

  // Parse extracted data from ocr_text JSON
  const parseExtracted = (ocr_text: string | null): Record<string, any> | null => {
    if (!ocr_text) return null;
    try {
      const jsonMatch = ocr_text.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) return JSON.parse(jsonMatch[1]);
      const clean = ocr_text.replace(/^---.*---\n?/gm, '').trim();
      return JSON.parse(clean);
    } catch { return null; }
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      {/* Left panel - queue list */}
      <div style={{
        width: selectedId ? '420px' : '100%',
        minWidth: '420px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #e5e7eb',
          background: '#fff',
        }}>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#1a1a1a', margin: 0 }}>
            {t('extraction.queue')} <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({items.length})</span>
          </h1>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', background: '#fafafa' }}>
          {items.map(inv => {
            const isSelected = selectedId === inv.id;
            const extracted = parseExtracted(inv.ocr_text);
            const sc = statusColors[inv.status] || statusColors.pending_review;

            return (
              <div
                key={inv.id}
                onClick={() => setSelectedId(isSelected ? null : inv.id)}
                style={{
                  padding: '14px 20px',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                  background: isSelected ? '#eff6ff' : '#fff',
                  borderLeft: isSelected ? '3px solid #0EA5E9' : '3px solid transparent',
                }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
              >
                {/* Filename + status + actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <FileText size={16} color={isSelected ? '#0EA5E9' : '#999'} />
                    <span style={{
                      fontSize: '13px', fontWeight: 600, color: '#1a1a1a',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {inv.original_filename}
                    </span>
                    <span style={{
                      padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                      background: sc.bg, color: sc.text, whiteSpace: 'nowrap', flexShrink: 0,
                    }}>
                      {sc.label}
                    </span>
                  </div>
                  {inv.status === 'pending_review' && (
                    <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                      <button onClick={() => handleApprove(inv.id)} style={{
                        padding: '4px 10px', background: '#10B981', color: '#fff',
                        border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px',
                        display: 'flex', alignItems: 'center', gap: '3px',
                      }}>
                        <CheckCircle size={12} /> OK
                      </button>
                      <button onClick={() => handleReject(inv.id)} style={{
                        padding: '4px 10px', background: '#EF4444', color: '#fff',
                        border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '11px',
                        display: 'flex', alignItems: 'center', gap: '3px',
                      }}>
                        <XCircle size={12} /> X
                      </button>
                    </div>
                  )}
                </div>

                {/* Extracted data grid */}
                <div style={{
                  display: 'grid', gridTemplateColumns: '1fr 1fr',
                  gap: '4px 16px', fontSize: '12px',
                }}>
                  <DataRow label={extracted?.szallito_nev ? 'Szállító' : 'Supplier'} value={extracted?.szallito_nev} />
                  <DataRow label="Számlaszám" value={inv.invoice_number || extracted?.szamla_szam} />
                  <DataRow label="Adószám" value={extracted?.szallito_adoszam} />
                  <DataRow label="Kelt" value={inv.invoice_date ? formatDate(inv.invoice_date) : extracted?.szamla_kelte} />
                  <DataRow label="Nettó" value={inv.net_amount != null ? formatCurrency(inv.net_amount, inv.currency) : null} highlight />
                  <DataRow label="ÁFA" value={inv.vat_amount != null ? `${formatCurrency(inv.vat_amount, inv.currency)} (${inv.vat_rate || extracted?.afa_kulcs || '?'}%)` : null} />
                  <DataRow label="Bruttó" value={inv.gross_amount != null ? formatCurrency(inv.gross_amount, inv.currency) : null} highlight />
                  <DataRow label="Fizetés" value={inv.payment_method || extracted?.fizetesi_mod} />
                </div>
              </div>
            );
          })}
          {items.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>
          )}
        </div>
      </div>

      {/* Right panel - PDF viewer + approval timeline */}
      {selectedId && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f3f4f6' }}>
          <div style={{
            padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#333' }}>
              {selected?.original_filename}
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
                Jóváhagyási folyamat
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
                            Jóváhagyom
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
                            Elutasítom
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
              <iframe src={pdfUrl} style={{ width: '100%', height: '100%', border: 'none' }} title="PDF" />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
                {t('common.loading')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reject modal */}
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
              Számla elutasítása
            </h3>
            <p style={{ margin: '0 0 16px', fontSize: '13px', color: '#666' }}>
              {rejectStep.step_name}
            </p>
            <textarea
              value={rejectComment}
              onChange={e => setRejectComment(e.target.value)}
              placeholder="Elutasítás indoka..."
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
                Mégse
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
                  <MessageSquare size={14} /> Elutasítás
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DataRow({ label, value, highlight }: { label: string; value: any; highlight?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '1px 0' }}>
      <span style={{ color: '#888' }}>{label}:</span>
      <span style={{
        color: value ? (highlight ? '#1a1a1a' : '#333') : '#ccc',
        fontWeight: highlight ? 600 : 400,
        maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {value || '-'}
      </span>
    </div>
  );
}
