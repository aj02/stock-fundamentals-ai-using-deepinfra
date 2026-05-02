'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FindingCard } from './finding-card';
import { fyLabel, formatINR, formatPct, formatRatio } from '@/lib/utils';
import type { FinancialsReport } from '@/lib/schema';

export function FinancialsSection({ report }: { report: FinancialsReport }) {
  const chartData = [...report.yearly_data]
    .reverse()
    .map((y) => ({
      label: fyLabel(y.period_end),
      revenue: y.revenue ? y.revenue / 1e7 : null,        // → ₹ crore
      operating_income: y.operating_income ? y.operating_income / 1e7 : null,
      net_income: y.net_income ? y.net_income / 1e7 : null,
    }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryStat label="Period" value={report.period_summary} />
        <SummaryStat label="Sector" value={report.sector ?? '—'} />
        <SummaryStat label="Currency" value={report.currency} />
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          <h3 className="text-sm font-semibold">Revenue, op income, net income (₹ cr)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toLocaleString('en-IN')}`} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })} cr`, '']}
                />
                <Bar dataKey="revenue" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
                <Bar dataKey="operating_income" fill="var(--color-positive)" radius={[2, 2, 0, 0]} />
                <Bar dataKey="net_income" fill="var(--color-warning)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-[color:var(--color-muted-foreground)]">
            <Legend color="var(--color-accent)" label="Revenue" />
            <Legend color="var(--color-positive)" label="Operating income" />
            <Legend color="var(--color-warning)" label="Net income" />
          </div>
        </CardContent>
      </Card>

      <RatiosTable report={report} />

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

      {report.data_quality_notes.length > 0 && (
        <Card>
          <CardContent className="space-y-2 p-5 text-xs text-[color:var(--color-muted-foreground)]">
            <h3 className="text-sm font-semibold text-[color:var(--color-foreground)]">Data quality notes</h3>
            <ul className="list-inside list-disc space-y-1">
              {report.data_quality_notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RatiosTable({ report }: { report: FinancialsReport }) {
  return (
    <Card>
      <CardContent className="overflow-x-auto p-5">
        <h3 className="mb-3 text-sm font-semibold">Ratios (newest first)</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[color:var(--color-border)] text-left text-xs text-[color:var(--color-muted-foreground)]">
              <th className="pb-2 pr-3">Period</th>
              <th className="pb-2 pr-3">Op mgn</th>
              <th className="pb-2 pr-3">Net mgn</th>
              <th className="pb-2 pr-3">ROE</th>
              <th className="pb-2 pr-3">ROCE</th>
              <th className="pb-2 pr-3">D/E</th>
              <th className="pb-2 pr-3">OCF/PAT</th>
              <th className="pb-2 pr-3">Curr ratio</th>
            </tr>
          </thead>
          <tbody>
            {report.ratios.yearly.map((r) => (
              <tr key={r.period_end} className="border-b border-[color:var(--color-border)]/50 last:border-none">
                <td className="py-1.5 pr-3 font-medium">{fyLabel(r.period_end)}</td>
                <td className="py-1.5 pr-3">{formatPct(r.operating_margin_pct)}</td>
                <td className="py-1.5 pr-3">{formatPct(r.net_margin_pct)}</td>
                <td className="py-1.5 pr-3">{formatPct(r.roe_pct)}</td>
                <td className="py-1.5 pr-3">{formatPct(r.roce_pct)}</td>
                <td className="py-1.5 pr-3">{formatRatio(r.debt_to_equity)}</td>
                <td className="py-1.5 pr-3">{formatRatio(r.ocf_to_pat)}</td>
                <td className="py-1.5 pr-3">{formatRatio(r.current_ratio)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-[color:var(--color-muted-foreground)]">
          Revenue CAGR (3y): {formatPct(report.ratios.growth.revenue_cagr_3y_pct)} ·{' '}
          Net income CAGR (3y): {formatPct(report.ratios.growth.net_income_cagr_3y_pct)} ·{' '}
          FCF CAGR (3y): {formatPct(report.ratios.growth.fcf_cagr_3y_pct)}
        </p>
      </CardContent>
    </Card>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs uppercase tracking-wide text-[color:var(--color-muted-foreground)]">{label}</div>
        <div className="mt-1 truncate font-medium">{value}</div>
      </CardContent>
    </Card>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="size-2.5 rounded-sm" style={{ background: color }} aria-hidden />
      {label}
    </span>
  );
}
