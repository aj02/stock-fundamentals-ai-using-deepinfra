import { TrendingDown, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { InvestmentThesis } from '@/lib/schema';

export function ThesisCard({ thesis, animate = false }: { thesis: InvestmentThesis; animate?: boolean }) {
  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 10 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="grid gap-4 md:grid-cols-2"
    >
      <ThesisColumn
        title="Bull case"
        icon={<TrendingUp className="size-4 text-[color:var(--color-positive)]" />}
        accent="positive"
        points={thesis.bull_case.map((p) => ({ point: p.point, citations: p.citations }))}
      />
      <ThesisColumn
        title="Bear case"
        icon={<TrendingDown className="size-4 text-[color:var(--color-negative)]" />}
        accent="negative"
        points={thesis.bear_case.map((p) => ({ point: p.point, citations: p.citations }))}
      />
      <Card className="md:col-span-2">
        <CardContent className="space-y-2 p-5">
          <h3 className="text-sm font-semibold">Neutral synthesis</h3>
          <p className="text-sm leading-relaxed text-[color:var(--color-muted-foreground)]">
            {thesis.neutral_summary}
          </p>
          {thesis.sections_unavailable.length > 0 && (
            <p className="pt-1 text-xs text-[color:var(--color-warning)]">
              Sections unavailable for this thesis: {thesis.sections_unavailable.join(', ')}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ThesisColumn({
  title,
  icon,
  accent,
  points,
}: {
  title: string;
  icon: React.ReactNode;
  accent: 'positive' | 'negative';
  points: { point: string; citations: { source_agent: string; finding_index: number; summary: string }[] }[];
}) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-sm font-semibold">{title}</h3>
          <Badge variant={accent} className="ml-auto">
            {points.length} {points.length === 1 ? 'point' : 'points'}
          </Badge>
        </div>
        <ol className="space-y-3 text-sm">
          {points.map((p, i) => (
            <li key={i} className="space-y-1">
              <div className="flex gap-2">
                <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-[color:var(--color-muted)] text-xs">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{p.point}</span>
              </div>
              <ul className="ml-7 space-y-0.5">
                {p.citations.map((c, j) => (
                  <li key={j} className="text-xs text-[color:var(--color-muted-foreground)]">
                    ↳ <span className="font-medium">{c.source_agent}</span>[{c.finding_index}]: {c.summary}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
