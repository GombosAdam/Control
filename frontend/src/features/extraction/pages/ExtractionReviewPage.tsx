import { useTranslation } from 'react-i18next';

export function ExtractionReviewPage() {
  const { t } = useTranslation();
  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '24px', color: '#1a1a1a' }}>
        {t('extraction.review')}
      </h1>
      <p style={{ color: '#666' }}>Select an invoice from the queue to review.</p>
    </div>
  );
}
