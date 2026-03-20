import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, CheckCircle, XCircle } from 'lucide-react';
import { invoicesApi } from '../../../services/api/invoices';

export function InvoiceUploadPage() {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<{ name: string; success: boolean; id?: string }[]>([]);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    const fileArray = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));

    for (const file of fileArray) {
      try {
        const result = await invoicesApi.upload(file);
        setResults(prev => [...prev, { name: file.name, success: true, id: result.id }]);
      } catch {
        setResults(prev => [...prev, { name: file.name, success: false }]);
      }
    }
    setUploading(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  return (
    <div style={{ padding: '24px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>
        {t('invoices.upload')}
      </h1>

      {/* Dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        style={{
          border: '2px dashed #d1d5db', borderRadius: '12px', padding: '48px',
          textAlign: 'center', cursor: 'pointer', background: '#fafafa',
          transition: 'border-color 200ms',
        }}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <Upload size={48} color="#999" style={{ marginBottom: '16px' }} />
        <p style={{ fontSize: '16px', color: '#666', margin: 0 }}>{t('invoices.uploadDrop')}</p>
        <p style={{ fontSize: '13px', color: '#999', marginTop: '8px' }}>PDF</p>
        <input
          id="file-input" type="file" accept=".pdf" multiple
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {uploading && (
        <div style={{ marginTop: '24px', textAlign: 'center', color: '#3B82F6' }}>
          {t('common.loading')}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          {results.map((r, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0',
              borderBottom: '1px solid #f3f4f6',
            }}>
              {r.success ? <CheckCircle size={16} color="#10B981" /> : <XCircle size={16} color="#EF4444" />}
              <span style={{ fontSize: '14px' }}>{r.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
