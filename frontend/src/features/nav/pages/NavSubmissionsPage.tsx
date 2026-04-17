import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { navApi, NavTransaction } from '../../../services/api/nav';
import { RefreshCw, Eye, X } from 'lucide-react';

const btnStyle: React.CSSProperties = {
  padding: '6px 12px', borderRadius: '6px', border: 'none',
  cursor: 'pointer', fontSize: '13px', fontWeight: 500,
};

const statusColors: Record<string, { bg: string; color: string }> = {
  pending: { bg: '#F3F4F6', color: '#6B7280' },
  sent: { bg: '#DBEAFE', color: '#2563EB' },
  processing: { bg: '#FEF3C7', color: '#D97706' },
  done: { bg: '#D1FAE5', color: '#059669' },
  aborted: { bg: '#FEE2E2', color: '#DC2626' },
  error: { bg: '#FEE2E2', color: '#DC2626' },
};

export function NavSubmissionsPage() {
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<NavTransaction[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedTxn, setSelectedTxn] = useState<NavTransaction | null>(null);

  const load = () => {
    navApi.listTransactions({ limit: 50, status: statusFilter || undefined })
      .then(data => setTransactions(data.items || []));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleRefresh = async (id: string) => {
    await navApi.refreshTransactionStatus(id);
    load();
  };

  const handleViewDetails = async (id: string) => {
    const data = await navApi.getTransaction(id);
    setSelectedTxn(data);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>{t('navSubmissions.title')}</h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px' }}>
            <option value="">{t('navSubmissions.allStatuses')}</option>
            <option value="pending">Pending</option>
            <option value="sent">Sent</option>
            <option value="processing">Processing</option>
            <option value="done">Done</option>
            <option value="aborted">Aborted</option>
            <option value="error">Error</option>
          </select>
          <button onClick={load} style={{ ...btnStyle, background: '#e5e7eb', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <RefreshCw size={14} /> {t('common.refresh')}
          </button>
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '10px' }}>{t('navSubmissions.invoiceNumber')}</th>
            <th style={{ padding: '10px' }}>{t('navSubmissions.operation')}</th>
            <th style={{ padding: '10px' }}>{t('navSubmissions.status')}</th>
            <th style={{ padding: '10px' }}>{t('navSubmissions.navTransactionId')}</th>
            <th style={{ padding: '10px' }}>{t('navSubmissions.error')}</th>
            <th style={{ padding: '10px' }}>{t('navSubmissions.createdAt')}</th>
            <th style={{ padding: '10px' }}>{t('common.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map(txn => {
            const sc = statusColors[txn.status] || { bg: '#f3f4f6', color: '#6b7280' };
            return (
              <tr key={txn.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '10px', fontWeight: 500 }}>{txn.invoice_number || '-'}</td>
                <td style={{ padding: '10px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '12px', background: '#f3f4f6', fontFamily: 'monospace' }}>
                    {txn.operation}
                  </span>
                </td>
                <td style={{ padding: '10px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: 500, background: sc.bg, color: sc.color }}>
                    {txn.status}
                  </span>
                </td>
                <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: '12px', color: '#6b7280' }}>
                  {txn.transaction_id || '-'}
                </td>
                <td style={{ padding: '10px', fontSize: '12px', color: '#dc2626', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={txn.error_message || ''}>
                  {txn.error_message || '-'}
                </td>
                <td style={{ padding: '10px', fontSize: '13px', color: '#6b7280' }}>
                  {new Date(txn.created_at).toLocaleString('hu-HU')}
                </td>
                <td style={{ padding: '10px' }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button onClick={() => handleViewDetails(txn.id)} title={t('navSubmissions.viewDetails')}
                      style={{ ...btnStyle, background: '#f3f4f6', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Eye size={14} />
                    </button>
                    {['sent', 'processing'].includes(txn.status) && (
                      <button onClick={() => handleRefresh(txn.id)} title={t('navSubmissions.refreshStatus')}
                        style={{ ...btnStyle, background: '#DBEAFE', color: '#2563EB', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <RefreshCw size={14} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
          {transactions.length === 0 && (
            <tr><td colSpan={7} style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>{t('navSubmissions.noTransactions')}</td></tr>
          )}
        </tbody>
      </table>

      {/* Detail modal */}
      {selectedTxn && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setSelectedTxn(null)}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', maxWidth: '800px', width: '90%', maxHeight: '80vh', overflow: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h2 style={{ margin: 0, fontSize: '18px' }}>{t('navSubmissions.transactionDetails')}</h2>
              <button onClick={() => setSelectedTxn(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px', fontSize: '14px' }}>
              <div><strong>{t('navSubmissions.invoiceNumber')}:</strong> {selectedTxn.invoice_number || '-'}</div>
              <div><strong>{t('navSubmissions.operation')}:</strong> {selectedTxn.operation}</div>
              <div><strong>{t('navSubmissions.status')}:</strong> {selectedTxn.status}</div>
              <div><strong>{t('navSubmissions.navTransactionId')}:</strong> {selectedTxn.transaction_id || '-'}</div>
              {selectedTxn.error_code && <div><strong>{t('navSubmissions.errorCode')}:</strong> {selectedTxn.error_code}</div>}
              {selectedTxn.error_message && <div style={{ gridColumn: '1 / -1' }}><strong>{t('navSubmissions.error')}:</strong> {selectedTxn.error_message}</div>}
            </div>
            {selectedTxn.request_xml && (
              <div style={{ marginBottom: '12px' }}>
                <h4 style={{ margin: '0 0 8px' }}>Request XML</h4>
                <pre style={{ background: '#f3f4f6', padding: '12px', borderRadius: '6px', fontSize: '12px', overflow: 'auto', maxHeight: '200px', whiteSpace: 'pre-wrap' }}>
                  {selectedTxn.request_xml}
                </pre>
              </div>
            )}
            {selectedTxn.response_xml && (
              <div>
                <h4 style={{ margin: '0 0 8px' }}>Response XML</h4>
                <pre style={{ background: '#f3f4f6', padding: '12px', borderRadius: '6px', fontSize: '12px', overflow: 'auto', maxHeight: '200px', whiteSpace: 'pre-wrap' }}>
                  {selectedTxn.response_xml}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
