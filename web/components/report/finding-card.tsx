import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { QualitativeFinding } from '@/lib/schema';

export function FindingCard({ finding, index }: { finding: QualitativeFinding; index: number }) {
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-[color:var(--color-muted-foreground)]">
            Finding {index + 1}
          </span>
          <Badge variant="outline" className="capitalize">
            {finding.category.replace(/_/g, ' ')}
          </Badge>
        </div>
        <p className="text-sm leading-relaxed">{finding.claim}</p>
        <ul className="space-y-1 border-l-2 border-[color:var(--color-border)] pl-3 text-xs">
          {finding.evidence.map((ev, i) => (
            <li key={i} className="text-[color:var(--color-muted-foreground)]">
              <span className="font-medium text-[color:var(--color-foreground)]">{ev.metric}</span>{' '}
              [{ev.years_referenced.join(', ')}] = [
              {ev.values.map((v) => formatValue(v)).join(', ')}]
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function formatValue(v: number): string {
  if (Math.abs(v) >= 1_000_000) {
    return v.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }
  if (Math.abs(v) >= 100) return v.toLocaleString('en-IN', { maximumFractionDigits: 1 });
  return v.toFixed(2);
}
