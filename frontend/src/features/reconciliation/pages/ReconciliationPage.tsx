import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GitCompareArrows, Zap, Link, Send, X } from 'lucide-react';
import { reconciliationApi } from '../../../services/api/reconciliation';
import { purchaseOrdersApi } from '../../../services/api/purchaseOrders';
import { invoicesApi } from '../../../services/api/invoices';
import { formatCurrency } from '../../../utils/formatters';
import type { PurchaseOrder } from '../../../types/controlling';

export function ReconciliationPage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [matchResult, setMatchResult] = useState<Record<string, any>>({});
  const [manualPO, setManualPO] = useState<string | null>(null);
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [selectedPO, setSelectedPO] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const load = () => {
    reconciliationApi.listPending({ page, limit: 50 })
      .then(data => { setItems(data.items); setTotal(data.total); });
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
  }, [selectedId]);

  const handleAutoMatch = async (invoiceId: string) => {
    const result = await reconciliationApi.autoMatch(invoiceId);
    setMatchResult(prev => ({ ...prev, [invoiceId]: result }));
    if (result.status === 'matched') {
      setTimeout(load, 500);
    }
  };

  const handleManualMatch = async (invoiceId: string) => {
    if (!selectedPO) return;
    const result = await reconciliationApi.manualMatch(invoiceId, selectedPO);
    setMatchResult(prev => ({ ...prev, [invoiceId]: result }));
    setManualPO(null);
    setSelectedPO('');
    if (result.status === 'matched') {
      setTimeout(load, 500);
    }
  };

  const handlePost = async (invoiceId: string) => {
    const result = await reconciliationApi.postToAccounting(invoiceId);
    setMatchResult(prev => ({ ...prev, [invoiceId]: result }));
    setTimeout(load, 500);
  };

  const openManual = async (invoiceId: string) => {
    setManualPO(invoiceId);
    const data = await purchaseOrdersApi.list({ status: 'approved', limit: 100 });
    setPos(data.items);
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh)', overflow: 'hidden' }}>
      <div style={{
        width: selectedId ? '55%' : '100%', minWidth: '600px',
        borderRight: selectedId ? '1px solid #e5e7eb' : 'none',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', background: '#fff' }}>
          <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitCompareArrows size={20} style={{ color: '#0d9488' }} />
            Egyeztetés <span style={{ fontSize: '13px', color: '#999', fontWeight: 400 }}>({total} egyeztetetlen)</span>
          </h1>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px' }}>
          {items.map(inv => (
            <div key={inv.id} style={{
              padding: '14px', marginBottom: '10px', background: '#fff', border: '1px solid #e5e7eb',
              borderRadius: '8px', cursor: 'pointer',
              borderLeft: selectedId === inv.id ? '3px solid #0d9488' : '3px solid transparent',
            }} onClick={() => setSelectedId(selectedId === inv.id ? null : inv.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px' }}>{inv.supplier_name || inv.original_filename}</div>
                  <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                    {inv.invoice_number && <span>#{inv.invoice_number} | </span>}
                    Adószám: {inv.supplier_tax_id || '-'} | {inv.invoice_date || '-'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>{formatCurrency(inv.gross_amount || 0, inv.currency)}</div>
                </div>
              </div>

              {/* Match result */}
              {matchResult[inv.id] && (
                <div style={{
                  marginTop: '8px', padding: '8px 12px', borderRadius: '6px', fontSize: '12px',
                  background: matchResult[inv.id].status === 'matched' ? '#d1fae5' : matchResult[inv.id].status === 'posted' ? '#dbeafe' : '#fef3c7',
                  color: matchResult[inv.id].status === 'matched' ? '#065f46' : matchResult[inv.id].status === 'posted' ? '#1e40af' : '#92400e',
                }}>
                  {matchResult[inv.id].status === 'matched' && `Egyeztetett: PO ${matchResult[inv.id].po_number} (${matchResult[inv.id].accounting_code})`}
                  {matchResult[inv.id].status === 'mismatch' && `Eltérés: ${matchResult[inv.id].reason}`}
                  {matchResult[inv.id].status === 'posted' && `Könyvelve: ${matchResult[inv.id].account_code} (${matchResult[inv.id].period})`}
                </div>
              )}

              {/* Manual match form */}
              {manualPO === inv.id && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center' }} onClick={e => e.stopPropagation()}>
                  <select value={selectedPO} onChange={e => setSelectedPO(e.target.value)} style={{
                    flex: 1, padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '12px',
                  }}>
                    <option value="">Válassz PO-t...</option>
                    {pos.map(po => (
                      <option key={po.id} value={po.id}>{po.po_number} - {po.supplier_name} ({formatCurrency(po.amount, po.currency)})</option>
                    ))}
                  </select>
                  <button onClick={() => handleManualMatch(inv.id)} style={smallBtn('#0d9488')}>Hozzárendelés</button>
                  <button onClick={() => { setManualPO(null); setSelectedPO(''); }} style={smallBtn('#999')}>
                    <X size={12} />
                  </button>
                </div>
              )}

              {/* Action buttons */}
              <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }} onClick={e => e.stopPropagation()}>
                <button onClick={() => handleAutoMatch(inv.id)} style={smallBtn('#0d9488')}>
                  <Zap size={12} /> Auto egyeztetés
                </button>
                <button onClick={() => openManual(inv.id)} style={smallBtn('#6B7280')}>
                  <Link size={12} /> Kézi hozzárendelés
                </button>
                {matchResult[inv.id]?.status === 'matched' && (
                  <button onClick={() => handlePost(inv.id)} style={smallBtn('#0EA5E9')}>
                    <Send size={12} /> Könyvelés
                  </button>
                )}
              </div>
            </div>
          ))}
          {items.length === 0 && <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>{t('common.noData')}</div>}
        </div>
      </div>

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

function smallBtn(color: string): React.CSSProperties {
  return {
    display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px',
    background: '#fff', border: `1px solid ${color}`, borderRadius: '4px',
    cursor: 'pointer', fontSize: '11px', color, fontWeight: 500,
  };
}
