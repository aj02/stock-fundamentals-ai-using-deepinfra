/**
 * Typed API client for the FastAPI backend.
 *
 * - Uses fetch() with JSON.
 * - Validates every response against a Zod schema; a parse failure throws
 *   instead of silently rendering a wrong shape.
 * - Reads NEXT_PUBLIC_API_BASE_URL at runtime; in dev defaults to localhost.
 */

import {
  analyzeResponseSchema,
  cancelResponseSchema,
  runFetchResponseSchema,
  tickersSearchResponseSchema,
  type AnalyzeResponse,
  type CancelResponse,
  type RunFetchResponse,
  type TickersSearchResponse,
} from './schema';

function apiBase(): string {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
  }
  // Server-side (Next.js fetch on the node runtime): default to backend
  // service name when running inside docker-compose.
  return process.env.API_BASE_URL_INTERNAL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://backend:8000';
}

export function wsBase(): string {
  if (typeof window !== 'undefined') {
    return (
      process.env.NEXT_PUBLIC_WS_BASE_URL
        ?? apiBase().replace(/^http/, 'ws')
    );
  }
  return process.env.NEXT_PUBLIC_WS_BASE_URL ?? 'ws://backend:8000';
}

class APIError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBase()}${path}`;
  const resp = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new APIError(resp.status, `${resp.status} ${resp.statusText}: ${body}`);
  }
  return (await resp.json()) as T;
}

export async function searchTickers(q: string): Promise<TickersSearchResponse> {
  const params = new URLSearchParams({ q, limit: '12' });
  const raw = await request<unknown>(`/tickers/search?${params.toString()}`);
  return tickersSearchResponseSchema.parse(raw);
}

export async function startAnalysis(
  ticker: string,
  opts: { depth?: 'quick' | 'full'; forceRefresh?: boolean } = {}
): Promise<AnalyzeResponse> {
  const raw = await request<unknown>('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      ticker,
      depth: opts.depth ?? 'full',
      force_refresh: opts.forceRefresh ?? false,
    }),
  });
  return analyzeResponseSchema.parse(raw);
}

export async function fetchRun(runId: string): Promise<RunFetchResponse> {
  const raw = await request<unknown>(`/runs/${runId}`);
  return runFetchResponseSchema.parse(raw);
}

export async function cancelRun(runId: string): Promise<CancelResponse> {
  const raw = await request<unknown>(`/runs/${runId}`, { method: 'DELETE' });
  return cancelResponseSchema.parse(raw);
}

export async function cancelAllRuns(): Promise<CancelResponse> {
  const raw = await request<unknown>('/runs/cancel-all', { method: 'POST' });
  return cancelResponseSchema.parse(raw);
}

export { APIError };
