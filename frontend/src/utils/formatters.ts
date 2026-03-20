export function formatCurrency(amount: number | null | undefined, currency: string = 'HUF'): string {
  if (amount == null) return '-';
  return new Intl.NumberFormat('hu-HU', {
    style: 'currency',
    currency,
    minimumFractionDigits: currency === 'HUF' ? 0 : 2,
    maximumFractionDigits: currency === 'HUF' ? 0 : 2,
  }).format(amount);
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('hu-HU');
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('hu-HU');
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '-';
  return `${(value * 100).toFixed(1)}%`;
}
