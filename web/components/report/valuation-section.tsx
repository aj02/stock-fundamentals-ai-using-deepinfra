'use client';

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FindingCard } from './finding-card';
import { fyLabel, formatINR, formatRatio, formatPct } from '@/lib/utils';
import type { ValuationReport } from '@/lib/schema';

export function ValuationSection({ report }: { report: ValuationReport }) {
  const cm = report.current_multiples;
  const peData = [...report.historical_valuation.yearly]
    .reverse()
    .filter((y) => y.pe != null && y.pe > 0)
    .map((y) => ({ label: fyLabel(y.period_end), pe: y.pe!, pb: y.pb }));

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Trailing P/E" value={formatRatio(cm.trailing_pe)} />
        <Stat label="Forward P/E" value={formatRatio(cm.forward_pe)} />
        <Stat label="P/B" value={formatRatio(cm.price_to_book)} />
        <Stat label="EV/EBITDA" value={formatRatio(cm.ev_to_ebitda)} />
        <Stat label="P/S (TTM)" value={formatRatio(cm.price_to_sales_ttm)} />
        <Stat label="EV/Revenue" value={formatRatio(cm.ev_to_revenue)} />
        <Stat label="Dividend yield" value={formatPct(cm.dividend_yield_pct)} />
        <Stat label="Payout ratio" value={formatPct(cm.payout_ratio_pct)} />
      </div>

      {peData.length >= 2 && (
        <Card>
          <CardContent className="space-y-3 p-5">
            <div className="flex items-end justify-between">
              <div>
                <h3 className="text-sm font-semibold">Historical P/E vs current</h3>
                <p className="text-xs text-[color:var(--color-muted-foreground)]">
                  Median P/E ({report.historical_valuation.medians.years_in_window}y):{' '}
                  {formatRatio(report.historical_valuation.medians.pe_median)}{' '}
                  · range {formatRatio(report.historical_valuation.medians.pe_min)}–
                  {formatRatio(report.historical_valuation.medians.pe_max)}
                </p>
              </div>
              <Badge variant="outline">Current {formatRatio(cm.trailing_pe)}</Badge>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={peData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-card)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  {report.historical_valuation.medians.pe_median != null && (
                    <ReferenceLine
                      y={report.historical_valuation.medians.pe_median}
                      stroke="var(--color-muted-foreground)"
                      strokeDasharray="4 4"
                      label={{ value: 'median', fontSize: 10, fill: 'var(--color-muted-foreground)' }}
                    />
                  )}
                  {cm.trailing_pe != null && (
                    <ReferenceLine
                      y={cm.trailing_pe}
                      stroke="var(--color-accent)"
                      strokeDasharray="2 2"
                      label={{ value: 'current', fontSize: 10, fill: 'var(--color-accent)' }}
                    />
                  )}
                  <Line
                    type="monotone"
                    dataKey="pe"
                    stroke="var(--color-accent)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <div>
        <h3 className="mb-3 text-sm font-semibold">
          Findings <Badge variant="secondary">{report.qualitative_assessment.length}</Badge>
        </h3>
        <div className="grid gap-3">
          {report.qualitative_assessment.map((f, i) => (
            <FindingCard key={i} finding={f} index={i} />
          ))}
        </div>
      </div>

      {!report.peer_comparison.available && (
        <Card>
          <CardContent className="p-4 text-xs text-[color:var(--color-muted-foreground)]">
            Peer comparison: <span className="italic">{report.peer_comparison.note}</span>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-3">
        <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-muted-foreground)]">
          {label}
        </div>
        <div className="mt-0.5 font-mono text-base">{value}</div>
      </CardContent>
    </Card>
  );
}
