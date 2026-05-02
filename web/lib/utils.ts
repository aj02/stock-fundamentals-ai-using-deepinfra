import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(value: number | null | undefined, opts?: { compact?: boolean }): string {
  if (value == null || !Number.isFinite(value)) return '—';
  if (opts?.compact) {
    if (Math.abs(value) >= 1e7) return `₹${(value / 1e7).toLocaleString('en-IN', { maximumFractionDigits: 1 })} cr`;
    if (Math.abs(value) >= 1e5) return `₹${(value / 1e5).toLocaleString('en-IN', { maximumFractionDigits: 1 })} L`;
    return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }
  return `₹${value.toLocaleString('en-IN')}`;
}

export function formatPct(value: number | null | undefined, decimals = 2): string {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${value.toFixed(decimals)}%`;
}

export function formatRatio(value: number | null | undefined, decimals = 2): string {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${value.toFixed(decimals)}×`;
}

export function shortDate(input: string | Date | null | undefined): string {
  if (!input) return '';
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function fyLabel(period: string | null | undefined): string {
  // "2026-03-31" → "FY26"
  if (!period) return '';
  const m = /^(\d{4})-/.exec(period);
  const year = m?.[1];
  if (!year) return period;
  return `FY${year.slice(-2)}`;
}
