import Link from 'next/link';
import type { Metadata } from 'next';
import { ArrowLeft } from 'lucide-react';
import { notFound } from 'next/navigation';

import { Card, CardContent } from '@/components/ui/card';
import { ReportTabs } from '@/components/report/report-tabs';
import { fetchRun, APIError } from '@/lib/api';

type PageProps = { params: Promise<{ run_id: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { run_id: runId } = await params;
  try {
    const data = await fetchRun(runId);
    const ticker = data.report.ticker;
    return {
      title: `${ticker} · fundamentals-ai`,
      description: `Multi-agent fundamental analysis report for ${ticker}. Educational demo, not investment advice.`,
      openGraph: {
        title: `${ticker} fundamental analysis`,
        description: 'Bull / bear synthesis with evidence-linked findings. Educational demo.',
      },
    };
  } catch {
    return { title: 'Report · fundamentals-ai' };
  }
}

export default async function ReportPage({ params }: PageProps) {
  const { run_id: runId } = await params;
  let payload;
  try {
    payload = await fetchRun(runId);
  } catch (err) {
    if (err instanceof APIError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  const r = payload.report;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]"
        >
          <ArrowLeft className="size-3.5" /> Search another ticker
        </Link>
      </div>

      <header className="mb-6">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <h1 className="font-mono text-3xl font-semibold tracking-tight">{r.ticker}</h1>
            <p className="text-sm text-[color:var(--color-muted-foreground)]">
              {r.financials?.company_name ?? r.valuation?.company_name ?? '—'}
            </p>
          </div>
          <div className="text-right text-xs text-[color:var(--color-muted-foreground)]">
            <div>Run {r.run_id.slice(0, 8)} · {r.depth} · {r.status}</div>
            {r.completed_at && <div>{new Date(r.completed_at).toLocaleString('en-IN')}</div>}
          </div>
        </div>
      </header>

      <Card className="mb-6 border-[color:var(--color-warning)]/30 bg-[color:var(--color-warning)]/5">
        <CardContent className="p-4 text-xs">
          <span className="font-medium">Disclaimer:</span> {r.disclaimer}
        </CardContent>
      </Card>

      <ReportTabs report={r} />

      <p className="mt-8 text-center text-xs text-[color:var(--color-muted-foreground)]">
        Generated on {r.completed_at ? new Date(r.completed_at).toLocaleString('en-IN') : '—'}.
        Data fetched from yfinance and Screener.in.
      </p>
    </div>
  );
}
