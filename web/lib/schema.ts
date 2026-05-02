/**
 * Zod schemas mirroring the backend's Pydantic models.
 *
 * Why: the frontend treats the backend as untrusted (defensive parse). If the
 * API ever ships a slightly different shape, the page should fail visibly
 * with a parse error rather than silently render garbage. Update both sides
 * together when contracts change.
 */

import { z } from 'zod';

// ─── Findings (shared shape) ───────────────────────────────────────────────
export const evidenceLinkSchema = z.object({
  metric: z.string(),
  years_referenced: z.array(z.number()),
  values: z.array(z.number()),
});

export const qualitativeFindingSchema = z.object({
  claim: z.string(),
  category: z.string(),
  evidence: z.array(evidenceLinkSchema),
});

// ─── Financials report ─────────────────────────────────────────────────────
const yearlyDataPointSchema = z.object({
  period_end: z.string(),
  revenue: z.number().nullable().optional(),
  operating_income: z.number().nullable().optional(),
  net_income: z.number().nullable().optional(),
  operating_cash_flow: z.number().nullable().optional(),
  free_cash_flow: z.number().nullable().optional(),
  total_debt: z.number().nullable().optional(),
  total_equity: z.number().nullable().optional(),
});

const yearlyRatiosSchema = z.object({
  period_end: z.string(),
  gross_margin_pct: z.number().nullable().optional(),
  operating_margin_pct: z.number().nullable().optional(),
  net_margin_pct: z.number().nullable().optional(),
  roe_pct: z.number().nullable().optional(),
  roce_pct: z.number().nullable().optional(),
  debt_to_equity: z.number().nullable().optional(),
  interest_coverage: z.number().nullable().optional(),
  current_ratio: z.number().nullable().optional(),
  ocf_to_pat: z.number().nullable().optional(),
  fcf_margin_pct: z.number().nullable().optional(),
});

export const financialsReportSchema = z.object({
  ticker: z.string(),
  yfinance_symbol: z.string(),
  company_name: z.string().nullable().optional(),
  sector: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
  currency: z.string(),
  period_summary: z.string(),
  yearly_data: z.array(yearlyDataPointSchema),
  ratios: z.object({
    yearly: z.array(yearlyRatiosSchema),
    growth: z.object({
      revenue_cagr_3y_pct: z.number().nullable().optional(),
      revenue_cagr_5y_pct: z.number().nullable().optional(),
      net_income_cagr_3y_pct: z.number().nullable().optional(),
      net_income_cagr_5y_pct: z.number().nullable().optional(),
      fcf_cagr_3y_pct: z.number().nullable().optional(),
    }),
  }),
  qualitative_assessment: z.array(qualitativeFindingSchema),
  data_quality_notes: z.array(z.string()),
  generated_at: z.string(),
  disclaimer: z.string(),
});

// ─── Valuation report ──────────────────────────────────────────────────────
export const valuationReportSchema = z.object({
  ticker: z.string(),
  yfinance_symbol: z.string(),
  company_name: z.string().nullable().optional(),
  sector: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
  currency: z.string(),
  period_summary: z.string(),
  current_multiples: z.object({
    current_price: z.number().nullable().optional(),
    market_cap: z.number().nullable().optional(),
    enterprise_value: z.number().nullable().optional(),
    trailing_pe: z.number().nullable().optional(),
    forward_pe: z.number().nullable().optional(),
    price_to_book: z.number().nullable().optional(),
    price_to_sales_ttm: z.number().nullable().optional(),
    ev_to_ebitda: z.number().nullable().optional(),
    ev_to_revenue: z.number().nullable().optional(),
    dividend_yield_pct: z.number().nullable().optional(),
    payout_ratio_pct: z.number().nullable().optional(),
    book_value_per_share: z.number().nullable().optional(),
    trailing_eps: z.number().nullable().optional(),
    forward_eps: z.number().nullable().optional(),
    fifty_two_week_high: z.number().nullable().optional(),
    fifty_two_week_low: z.number().nullable().optional(),
    fetched_at: z.string(),
  }),
  historical_valuation: z.object({
    yearly: z.array(z.object({
      period_end: z.string(),
      fy_end_close_price: z.number().nullable().optional(),
      eps_for_year: z.number().nullable().optional(),
      book_value_per_share: z.number().nullable().optional(),
      pe: z.number().nullable().optional(),
      pb: z.number().nullable().optional(),
    })),
    medians: z.object({
      pe_median: z.number().nullable().optional(),
      pb_median: z.number().nullable().optional(),
      pe_min: z.number().nullable().optional(),
      pe_max: z.number().nullable().optional(),
      pb_min: z.number().nullable().optional(),
      pb_max: z.number().nullable().optional(),
      years_in_window: z.number(),
    }),
  }),
  peer_comparison: z.object({
    available: z.boolean(),
    peers: z.array(z.unknown()),
    peer_pe_median: z.number().nullable().optional(),
    peer_pb_median: z.number().nullable().optional(),
    note: z.string(),
    fetched_at: z.string(),
  }),
  qualitative_assessment: z.array(qualitativeFindingSchema),
  data_quality_notes: z.array(z.string()),
  generated_at: z.string(),
  disclaimer: z.string(),
});

// ─── Management & Risk ─────────────────────────────────────────────────────
const textEvidenceSchema = z.object({
  quote: z.string(),
  section: z.string(),
  page: z.number().nullable().optional(),
});

const managementFindingSchema = z.object({
  claim: z.string(),
  category: z.string(),
  evidence: z.array(textEvidenceSchema),
});

export const managementReportSchema = z.object({
  ticker: z.string(),
  yfinance_symbol: z.string(),
  company_name: z.string().nullable().optional(),
  fiscal_year: z.number().nullable().optional(),
  annual_report_url: z.string().nullable().optional(),
  annual_report_page_count: z.number().nullable().optional(),
  mda_findings: z.array(managementFindingSchema),
  governance_findings: z.array(managementFindingSchema),
  data_quality_notes: z.array(z.string()),
  generated_at: z.string(),
  disclaimer: z.string(),
});

const riskEvidenceSchema = z.object({
  quote: z.string(),
  source: z.enum(['annual_report', 'screener_concern', 'mda']),
  section: z.string().nullable().optional(),
  page: z.number().nullable().optional(),
});

const riskFindingSchema = z.object({
  risk: z.string(),
  category: z.string(),
  severity: z.enum(['low', 'medium', 'high']),
  mitigation_summary: z.string().nullable().optional(),
  evidence: z.array(riskEvidenceSchema),
});

export const riskReportSchema = z.object({
  ticker: z.string(),
  yfinance_symbol: z.string(),
  company_name: z.string().nullable().optional(),
  fiscal_year: z.number().nullable().optional(),
  annual_report_url: z.string().nullable().optional(),
  risks: z.array(riskFindingSchema),
  screener_concerns_used: z.boolean(),
  data_quality_notes: z.array(z.string()),
  generated_at: z.string(),
  disclaimer: z.string(),
});

// ─── Thesis ────────────────────────────────────────────────────────────────
const thesisCitationSchema = z.object({
  source_agent: z.enum(['financials', 'valuation', 'management', 'risk']),
  finding_index: z.number(),
  summary: z.string(),
});

const thesisPointSchema = z.object({
  point: z.string(),
  citations: z.array(thesisCitationSchema),
});

export const investmentThesisSchema = z.object({
  ticker: z.string(),
  company_name: z.string().nullable().optional(),
  bull_case: z.array(thesisPointSchema),
  bear_case: z.array(thesisPointSchema),
  neutral_summary: z.string(),
  sections_unavailable: z.array(z.string()),
  generated_at: z.string(),
  disclaimer: z.string(),
});

// ─── RunReport ─────────────────────────────────────────────────────────────
export const sectionUnavailableSchema = z.object({
  section: z.string(),
  reason: z.string(),
});

export const runReportSchema = z.object({
  run_id: z.string(),
  ticker: z.string(),
  depth: z.enum(['quick', 'full']),
  status: z.enum(['queued', 'running', 'completed', 'failed', 'cancelled']),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  duration_seconds: z.number().nullable().optional(),
  financials: financialsReportSchema.nullable().optional(),
  valuation: valuationReportSchema.nullable().optional(),
  management: managementReportSchema.nullable().optional(),
  risk: riskReportSchema.nullable().optional(),
  thesis: investmentThesisSchema.nullable().optional(),
  unavailable_sections: z.array(sectionUnavailableSchema),
  error: z.string().nullable().optional(),
  disclaimer: z.string(),
});

export const analyzeResponseSchema = z.object({
  run_id: z.string(),
  websocket_url: z.string(),
  status_url: z.string(),
  cached: z.boolean().optional().default(false),
  disclaimer: z.string(),
});

export const cancelResponseSchema = z.object({
  cancelled: z.array(z.string()),
  disclaimer: z.string(),
});

export const runFetchResponseSchema = z.object({
  run_id: z.string(),
  report: runReportSchema,
  disclaimer: z.string(),
});

export const tickerInfoSchema = z.object({
  ticker: z.string(),
  name: z.string(),
  sector: z.string(),
  exchange: z.string(),
});

export const tickersSearchResponseSchema = z.object({
  query: z.string(),
  results: z.array(tickerInfoSchema),
  disclaimer: z.string(),
});

// ─── Run events (matches app/agents/events.py) ─────────────────────────────
export const runEventSchema = z.object({
  type: z.string(),
  run_id: z.string(),
  timestamp: z.string(),
  // Agent / tool / thesis events all carry a different shape; just keep the
  // payload as a passthrough record.
}).passthrough();

// ─── TS aliases ────────────────────────────────────────────────────────────
export type FinancialsReport = z.infer<typeof financialsReportSchema>;
export type ValuationReport = z.infer<typeof valuationReportSchema>;
export type ManagementReport = z.infer<typeof managementReportSchema>;
export type RiskReport = z.infer<typeof riskReportSchema>;
export type InvestmentThesis = z.infer<typeof investmentThesisSchema>;
export type RunReport = z.infer<typeof runReportSchema>;
export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>;
export type CancelResponse = z.infer<typeof cancelResponseSchema>;
export type RunFetchResponse = z.infer<typeof runFetchResponseSchema>;
export type TickerInfo = z.infer<typeof tickerInfoSchema>;
export type TickersSearchResponse = z.infer<typeof tickersSearchResponseSchema>;
export type RunEvent = z.infer<typeof runEventSchema>;
export type QualitativeFinding = z.infer<typeof qualitativeFindingSchema>;
export type EvidenceLink = z.infer<typeof evidenceLinkSchema>;
