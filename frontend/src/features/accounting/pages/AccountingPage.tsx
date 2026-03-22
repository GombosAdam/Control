import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Search, Send, BookOpen } from 'lucide-react';
import { accountingApi } from '../../../services/api/accounting';
import { reconciliationApi } from '../../../services/api/reconciliation';
import { invoicesApi } from '../../../services/api/invoices';
import { formatCurrency } from '../../../utils/formatters';

export function AccountingPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [summary, setSummary] = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [entries, setEntries] = useState<any[]>([]);
  const [postingId, setPostingId] = useState<string | null>(null);

  const load = () => {
    accountingApi.listInvoices({ page, limit: 50, search: search || undefined })
      .then(data => { setItems(data.items); setTotal(data.total); });
    accountingApi.getSummary().then(setSummary);
  };

  useEffect(() => { load(); }, [page]);

  useEffect(() => {
    if (!selectedId) {
      if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }
      setEntries([]);
      return;
    }
    invoicesApi.getPdf(selectedId).then(blob => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
    });
    // Load entries for this invoice
    accountingApi.listEntries({ invoice_id: selectedId, limit: 50 }).then(data => {
      setEntries(data.items);
    });
  }, [selectedId]);

  const handlePost = async (invoiceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPostingId(invoiceId);
    try {
      await reconciliationApi.postToAccounting(invoiceId);
      load();
      // Refresh entries if this invoice is selected
      if (selectedId === invoiceId) {
        accountingApi.listEntries({ invoice_id: invoiceId, limit: 50 }).then(data => {
          setEntries(data.items);
        });
      }
    } catch { }
    setPostingId(null);
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      {/* Left panel */}
      <div style={{
        width: selectedId ? '55%' : '100%', minWidth: '600px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#1a1a1a', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={20} style={{ color: '#0EA5E9' }} />
              Könyvelés <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total})</span>
            </h1>
          </div>

          {summary && (
            <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
              <SummaryCard label="Nettó összesen" value={formatCurrency(summary.total_net)} color="#3B82F6" />
              <SummaryCard label="ÁFA összesen" value={formatCurrency(summary.total_vat)} color="#F59E0B" />
              <SummaryCard label="Bruttó összesen" value={formatCurrency(summary.total_gross)} color="#10B981" />
              {summary.by_currency?.map((c: any) => (
                <SummaryCard key={c.currency} label={c.currency} value={`${c.count} db`} color="#0EA5E9" />
              ))}
            </div>
          )}

          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
            <input type="text" placeholder="Keresés (számlaszám, fájlnév)..." value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && load()}
              style={{ width: '100%', padding: '8px 10px 8px 32px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '13px', outline: 'none', boxSizing: 'border-box' }} />
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb', position: 'sticky', top: 0 }}>
                {['Szállító', 'Számlaszám', 'PO szám', 'Státusz', 'Adószám', 'Kelt', 'Nettó', 'ÁFA', 'Bruttó', 'Deviza', ''].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#666', textTransform: 'uppercase', fontSize: '10px', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(inv => (
                <tr key={inv.id}
                  onClick={() => setSelectedId(selectedId === inv.id ? null : inv.id)}
                  style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer', background: selectedId === inv.id ? '#eff6ff' : '#fff' }}
                  onMouseEnter={(e) => { if (selectedId !== inv.id) e.currentTarget.style.background = '#f9fafb'; }}
                  onMouseLeave={(e) => { if (selectedId !== inv.id) e.currentTarget.style.background = '#fff'; }}
                >
                  <td style={{ padding: '8px 10px', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                    {inv.szallito_nev || '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#3B82F6', fontWeight: 500 }}>
                    {inv.invoice_number || '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#06B6D4', fontWeight: 600, fontSize: '11px' }}>
                    {inv.po_number || '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>
                    <span style={{
                      padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                      background: inv.status === 'posted' ? '#dcfce7' : '#dbeafe',
                      color: inv.status === 'posted' ? '#166534' : '#1e40af',
                    }}>
                      {inv.status === 'posted' ? 'Könyvelve' : 'Párosítva'}
                    </span>
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#666', fontFamily: 'monospace', fontSize: '11px' }}>
                    {inv.szallito_adoszam || '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#666' }}>
                    {inv.invoice_date || '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', textAlign: 'right' }}>
                    {inv.net_amount != null ? formatCurrency(inv.net_amount, inv.currency) : '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', textAlign: 'right', color: '#666' }}>
                    {inv.vat_amount != null ? formatCurrency(inv.vat_amount, inv.currency) : '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', textAlign: 'right', fontWeight: 600 }}>
                    {inv.gross_amount != null ? formatCurrency(inv.gross_amount, inv.currency) : '-'}
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600, background: '#dbeafe', color: '#1e40af' }}>
                      {inv.currency}
                    </span>
                  </td>
                  <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }} onClick={e => e.stopPropagation()}>
                    {inv.status === 'matched' && (
                      <button onClick={(e) => handlePost(inv.id, e)} disabled={postingId === inv.id}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px',
                          background: '#0EA5E9', color: '#fff', border: 'none', borderRadius: '4px',
                          cursor: 'pointer', fontSize: '11px', fontWeight: 600,
                          opacity: postingId === inv.id ? 0.5 : 1,
                        }}>
                        <Send size={12} /> Könyvelés
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>Nincs egyeztetett számla</div>
          )}
        </div>

        {total > 50 && (
          <div style={{ padding: '8px 20px', borderTop: '1px solid #e5e7eb', background: '#fff', display: 'flex', justifyContent: 'center', gap: '8px', alignItems: 'center' }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              style={{ padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: '4px', background: '#fff', cursor: 'pointer', fontSize: '12px', opacity: page === 1 ? 0.5 : 1 }}>
              {t('common.previous')}
            </button>
            <span style={{ fontSize: '12px', color: '#666' }}>{page} / {Math.ceil(total / 50)}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 50)}
              style={{ padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: '4px', background: '#fff', cursor: 'pointer', fontSize: '12px', opacity: page >= Math.ceil(total / 50) ? 0.5 : 1 }}>
              {t('common.next')}
            </button>
          </div>
        )}
      </div>

      {/* Right panel - PDF + Entries */}
      {selectedId && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f3f4f6' }}>
          <div style={{ padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 500, color: '#333' }}>
              {items.find(i => i.id === selectedId)?.original_filename}
            </span>
            <button onClick={() => setSelectedId(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#666' }}>
              <X size={18} />
            </button>
          </div>

          {/* Accounting entries for this invoice */}
          {entries.length > 0 && (
            <div style={{ padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#666', marginBottom: '8px', textTransform: 'uppercase' }}>
                Könyvelési tételek
              </div>
              <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600 }}>Számla</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600 }}>Típus</th>
                    <th style={{ padding: '4px 8px', textAlign: 'right', color: '#888', fontWeight: 600 }}>Összeg</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left', color: '#888', fontWeight: 600 }}>Időszak</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e: any) => (
                    <tr key={e.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '4px 8px', fontFamily: 'monospace', fontWeight: 600 }}>{e.account_code}</td>
                      <td style={{ padding: '4px 8px' }}>
                        <span style={{
                          padding: '1px 6px', borderRadius: '3px', fontSize: '10px', fontWeight: 600,
                          background: e.entry_type === 'debit' ? '#fef3c7' : '#d1fae5',
                          color: e.entry_type === 'debit' ? '#92400e' : '#065f46',
                        }}>
                          {e.entry_type === 'debit' ? 'T' : 'K'}
                        </span>
                      </td>
                      <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>
                        {formatCurrency(e.amount, e.currency)}
                      </td>
                      <td style={{ padding: '4px 8px', color: '#666' }}>{e.period}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: '8px 14px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '6px', borderLeft: `3px solid ${color}` }}>
      <p style={{ margin: 0, fontSize: '10px', color: '#888', textTransform: 'uppercase' }}>{label}</p>
      <p style={{ margin: '2px 0 0', fontSize: '14px', fontWeight: 600, color: '#1a1a1a' }}>{value}</p>
    </div>
  );
}
