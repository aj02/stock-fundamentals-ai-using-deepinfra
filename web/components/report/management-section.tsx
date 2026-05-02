import { ExternalLink } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { ManagementReport } from '@/lib/schema';

export function ManagementSection({ report }: { report: ManagementReport }) {
  if (report.mda_findings.length === 0 && report.governance_findings.length === 0) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-[color:var(--color-muted-foreground)]">
          Management section unavailable for this run.
          {report.data_quality_notes.length > 0 && (
            <ul className="mt-2 list-inside list-disc text-xs">
              {report.data_quality_notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {report.annual_report_url && (
        <p className="text-xs text-[color:var(--color-muted-foreground)]">
          Drawn from FY{report.fiscal_year} annual report{' '}
          {report.annual_report_page_count ? `(${report.annual_report_page_count} pages)` : ''} ·{' '}
          <a
            href={report.annual_report_url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-0.5 underline-offset-2 hover:underline"
          >
            source PDF <ExternalLink className="size-3" />
          </a>
        </p>
      )}

      <FindingsBlock title="Management Discussion & Analysis" findings={report.mda_findings} />
      <FindingsBlock title="Corporate Governance" findings={report.governance_findings} />

      {report.data_quality_notes.length > 0 && (
        <Card>
          <CardContent className="space-y-1 p-5 text-xs text-[color:var(--color-muted-foreground)]">
            <h4 className="text-sm font-semibold text-[color:var(--color-foreground)]">Data quality notes</h4>
            <ul className="list-inside list-disc">
              {report.data_quality_notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function FindingsBlock({ title, findings }: { title: string; findings: ManagementReport['mda_findings'] }) {
  if (findings.length === 0) return null;
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold">
        {title} <Badge variant="secondary">{findings.length}</Badge>
      </h3>
      <div className="grid gap-3">
        {findings.map((f, i) => (
          <Card key={i}>
            <CardContent className="space-y-3 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[color:var(--color-muted-foreground)]">
                  Finding {i + 1}
                </span>
                <Badge variant="outline" className="capitalize">
                  {f.category.replace(/_/g, ' ')}
                </Badge>
              </div>
              <p className="text-sm leading-relaxed">{f.claim}</p>
              {f.evidence.map((ev, j) => (
                <blockquote
                  key={j}
                  className="border-l-2 border-[color:var(--color-border)] pl-3 text-xs italic text-[color:var(--color-muted-foreground)]"
                >
                  &ldquo;{ev.quote}&rdquo;
                  <span className="not-italic"> — {ev.section}{ev.page ? `, p.${ev.page}` : ''}</span>
                </blockquote>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
