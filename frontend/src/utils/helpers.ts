import { format, parseISO } from 'date-fns';

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    return format(parseISO(dateStr), 'MMM dd, yyyy');
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    return format(parseISO(dateStr), 'MMM dd, yyyy HH:mm');
  } catch {
    return dateStr;
  }
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return '-';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return '-';
  return value.toFixed(decimals);
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'badge-gray',
    planned: 'badge-gray',
    pending: 'badge-yellow',
    confirmed: 'badge-blue',
    approved: 'badge-blue',
    released: 'badge-blue',
    allocated: 'badge-blue',
    in_production: 'badge-yellow',
    sent: 'badge-blue',
    shipped: 'badge-blue',
    partially_received: 'badge-yellow',
    received: 'badge-green',
    completed: 'badge-green',
    invoiced: 'badge-green',
    closed: 'badge-gray',
    available: 'badge-green',
    on_hold: 'badge-yellow',
    qc_hold: 'badge-yellow',
    rejected: 'badge-red',
    cancelled: 'badge-red',
    passed: 'badge-green',
    failed: 'badge-red',
  };
  return colors[status] || 'badge-gray';
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
