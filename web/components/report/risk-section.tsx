import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { RiskReport } from '@/lib/schema';

const SEVERITY_VARIANT: Record<'low' | 'medium' | 'high', 'positive' | 'warning' | 'negative'> = {
  low: 'positive',
  medium: 'warning',
  high: 'negative',
};

export function RiskSection({ report }: { report: RiskReport }) {
  if (report.risks.length === 0) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-[color:var(--color-muted-foreground)]">
          Risk section returned no findings for this run.
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">
          Risks <Badge variant="secondary">{report.risks.length}</Badge>
        </h3>
        {report.screener_concerns_used && (
          <Badge variant="outline">includes Screener concerns</Badge>
        )}
      </div>
      {report.risks.map((r, i) => (
        <Card key={i}>
          <CardContent className="space-y-3 p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm font-medium leading-relaxed">{r.risk}</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="outline" className="capitalize">
                    {r.category}
                  </Badge>
                  <Badge variant={SEVERITY_VARIANT[r.severity]}>{r.severity} severity</Badge>
                </div>
              </div>
            </div>
            {r.mitigation_summary && (
              <p className="rounded-md bg-[color:var(--color-muted)] p-3 text-xs">
                <span className="font-medium">Mitigation per company: </span>
                {r.mitigation_summary}
              </p>
            )}
            {r.evidence.map((ev, j) => (
              <blockquote
                key={j}
                className="border-l-2 border-[color:var(--color-border)] pl-3 text-xs italic text-[color:var(--color-muted-foreground)]"
              >
                &ldquo;{ev.quote}&rdquo;
                <span className="not-italic"> — {sourceLabel(ev.source, ev.section)}{ev.page ? `, p.${ev.page}` : ''}</span>
              </blockquote>
            ))}
          </CardContent>
        </Card>
      ))}
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

function sourceLabel(source: string, section?: string | null): string {
  if (source === 'screener_concern') return 'Screener.in';
  if (source === 'mda') return 'AR · MD&A';
  if (source === 'annual_report') return `AR · ${section ?? 'risks'}`;
  return source;
}
