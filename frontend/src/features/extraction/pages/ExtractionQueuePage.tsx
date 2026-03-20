import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, XCircle, X, FileText } from 'lucide-react';
import { extractionApi } from '../../../services/api/extraction';
import { invoicesApi } from '../../../services/api/invoices';
import { formatCurrency, formatDate } from '../../../utils/formatters';

export function ExtractionQueuePage() {
  const { t } = useTranslation();
  const [items, setItems] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const load = () => { extractionApi.getQueue({ limit: 50 }).then(data => setItems(data.items)); };
  useEffect(() => { load(); }, []);

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

  const handleApprove = async (id: string) => {
    await extractionApi.approve(id);
    if (selectedId === id) setSelectedId(null);
    load();
  };

  const handleReject = async (id: string) => {
    await extractionApi.reject(id);
    if (selectedId === id) setSelectedId(null);
    load();
  };

  const selected = items.find(i => i.id === selectedId);

  // Parse extracted data from ocr_text JSON
  const parseExtracted = (ocr_text: string | null): Record<string, any> | null => {
    if (!ocr_text) return null;
    try {
      const jsonMatch = ocr_text.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) return JSON.parse(jsonMatch[1]);
      // Try direct JSON parse
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

            return (
              <div
                key={inv.id}
                onClick={() => setSelectedId(isSelected ? null : inv.id)}
                style={{
                  padding: '14px 20px',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                  background: isSelected ? '#eff6ff' : '#fff',
                  borderLeft: isSelected ? '3px solid #8B5CF6' : '3px solid transparent',
                }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f9fafb'; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
              >
                {/* Filename + actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <FileText size={16} color={isSelected ? '#8B5CF6' : '#999'} />
                    <span style={{
                      fontSize: '13px', fontWeight: 600, color: '#1a1a1a',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {inv.original_filename}
                    </span>
                  </div>
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

      {/* Right panel - PDF viewer */}
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
