import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, X, MessageSquare } from 'lucide-react';
import { invoicesApi } from '../../../services/api/invoices';
import { useAuthStore } from '../../../stores/authStore';
import { formatDate } from '../../../utils/formatters';
import type { ApprovalQueueItem } from '../../../types/invoice';

export function ApprovalQueuePage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [items, setItems] = useState<ApprovalQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<ApprovalQueueItem | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    invoicesApi.getApprovalQueue(user?.role)
      .then(data => setItems(data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleApprove = async (item: ApprovalQueueItem) => {
    setActionLoading(item.invoice_id);
    try {
      await invoicesApi.decideApproval(item.invoice_id, item.step, 'approved');
      load();
    } catch { }
    setActionLoading(null);
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    setActionLoading(rejectTarget.invoice_id);
    try {
      await invoicesApi.decideApproval(rejectTarget.invoice_id, rejectTarget.step, 'rejected', rejectComment || undefined);
      setRejectTarget(null);
      setRejectComment('');
      load();
    } catch { }
    setActionLoading(null);
  };

  const formatAmount = (amount: number | null, currency: string) => {
    if (amount == null) return '-';
    return new Intl.NumberFormat('hu-HU', { style: 'currency', currency }).format(amount);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px' }}>
      <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#1a1a1a', marginBottom: '20px' }}>
        {t('approvals.title', 'Approval Queue')}
      </h1>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.loading')}</div>
      ) : items.length === 0 ? (
        <div style={{
          padding: '60px', textAlign: 'center', color: '#999',
          background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb',
        }}>
          {t('approvals.empty', 'Nincs jóváhagyásra váró számla')}
        </div>
      ) : (
        <div style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#666' }}>
                  {t('approvals.filename', 'Fájlnév')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#666' }}>
                  {t('approvals.invoiceNumber', 'Számlaszám')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 600, color: '#666' }}>
                  {t('approvals.amount', 'Összeg')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#666' }}>
                  {t('approvals.step', 'Lépés')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#666' }}>
                  {t('approvals.role', 'Várakozik')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#666' }}>
                  {t('approvals.date', 'Dátum')}
                </th>
                <th style={{ padding: '10px 16px', textAlign: 'center', fontWeight: 600, color: '#666' }}>
                  {t('approvals.actions', 'Műveletek')}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={`${item.invoice_id}-${item.step}`} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '10px 16px', color: '#1a1a1a' }}>
                    {item.original_filename || '-'}
                  </td>
                  <td style={{ padding: '10px 16px', color: '#666' }}>
                    {item.invoice_number || '-'}
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 500, color: '#1a1a1a' }}>
                    {formatAmount(item.gross_amount, item.currency)}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                      background: '#fef3c7', color: '#92400e',
                    }}>
                      {item.step_name}
                    </span>
                  </td>
                  <td style={{ padding: '10px 16px', color: '#666' }}>
                    {item.assigned_role}
                  </td>
                  <td style={{ padding: '10px 16px', color: '#999', fontSize: '12px' }}>
                    {formatDate(item.created_at)}
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                      <button
                        onClick={() => handleApprove(item)}
                        disabled={actionLoading === item.invoice_id}
                        style={{
                          padding: '4px 12px', borderRadius: '4px', border: 'none',
                          background: '#10B981', color: '#fff', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: '4px',
                          fontSize: '12px', fontWeight: 500, opacity: actionLoading === item.invoice_id ? 0.5 : 1,
                        }}
                      >
                        <Check size={12} /> {t('approvals.approve', 'Jóváhagyás')}
                      </button>
                      <button
                        onClick={() => setRejectTarget(item)}
                        disabled={actionLoading === item.invoice_id}
                        style={{
                          padding: '4px 12px', borderRadius: '4px', border: 'none',
                          background: '#EF4444', color: '#fff', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: '4px',
                          fontSize: '12px', fontWeight: 500, opacity: actionLoading === item.invoice_id ? 0.5 : 1,
                        }}
                      >
                        <X size={12} /> {t('approvals.reject', 'Elutasítás')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {rejectTarget && (
        <div
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 300,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          onClick={() => { setRejectTarget(null); setRejectComment(''); }}
        >
          <div
            style={{
              background: '#fff', borderRadius: '12px', padding: '24px',
              width: '400px', maxWidth: '90vw',
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 600 }}>
              {t('approvals.rejectTitle', 'Számla elutasítása')}
            </h3>
            <p style={{ margin: '0 0 16px', fontSize: '13px', color: '#666' }}>
              {rejectTarget.original_filename} — {rejectTarget.step_name}
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
                onClick={() => { setRejectTarget(null); setRejectComment(''); }}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: '1px solid #d1d5db',
                  background: '#fff', cursor: 'pointer', fontSize: '13px',
                }}
              >
                {t('common.cancel', 'Mégse')}
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading === rejectTarget.invoice_id}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: 'none',
                  background: '#EF4444', color: '#fff', cursor: 'pointer',
                  fontSize: '13px', fontWeight: 500,
                  opacity: actionLoading === rejectTarget.invoice_id ? 0.5 : 1,
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
    </div>
  );
}
