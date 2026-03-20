import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Upload, FileText, X } from 'lucide-react';
import { invoicesApi } from '../../../services/api/invoices';
import { formatDate } from '../../../utils/formatters';
import type { Invoice } from '../../../types/invoice';

export function InvoiceListPage() {
  const { t } = useTranslation();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const load = () => {
    invoicesApi.list({ page, limit: 50 })
      .then(data => { setInvoices(data.items); setTotal(data.total); });
  };

  useEffect(() => { load(); }, [page]);

  useEffect(() => {
    if (!selectedId) {
      if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }
      return;
    }
    invoicesApi.getPdf(selectedId).then(blob => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
    });
    return () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl); };
  }, [selectedId]);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      {/* Left panel - invoice list */}
      <div style={{
        width: selectedId ? '360px' : '100%',
        minWidth: '360px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
        transition: 'width 200ms ease',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #e5e7eb',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#fff',
        }}>
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

        {/* Invoice list */}
        <div style={{ flex: 1, overflowY: 'auto', background: '#fafafa' }}>
          {invoices.map(inv => (
            <div
              key={inv.id}
              onClick={() => setSelectedId(selectedId === inv.id ? null : inv.id)}
              style={{
                padding: '12px 20px',
                borderBottom: '1px solid #f0f0f0',
                cursor: 'pointer',
                background: selectedId === inv.id ? '#eff6ff' : '#fff',
                borderLeft: selectedId === inv.id ? '3px solid #3B82F6' : '3px solid transparent',
                transition: 'all 100ms ease',
              }}
              onMouseEnter={(e) => { if (selectedId !== inv.id) e.currentTarget.style.background = '#f9fafb'; }}
              onMouseLeave={(e) => { if (selectedId !== inv.id) e.currentTarget.style.background = '#fff'; }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={18} color={selectedId === inv.id ? '#3B82F6' : '#999'} strokeWidth={1.5} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    margin: 0, fontSize: '14px', fontWeight: 500, color: '#1a1a1a',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {inv.original_filename}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#999' }}>
                    {formatDate(inv.created_at)}
                  </p>
                </div>
              </div>
            </div>
          ))}
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
          {/* PDF header */}
          <div style={{
            padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#333' }}>
              {invoices.find(i => i.id === selectedId)?.original_filename}
            </span>
            <button
              onClick={() => setSelectedId(null)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', padding: '4px',
                color: '#666', display: 'flex', alignItems: 'center',
              }}
            >
              <X size={18} />
            </button>
          </div>

          {/* PDF embed */}
          <div style={{ flex: 1, padding: '0' }}>
            {pdfUrl ? (
              <iframe
                src={pdfUrl}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="PDF Preview"
              />
            ) : (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100%', color: '#999',
              }}>
                {t('common.loading')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
