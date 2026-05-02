import Link from 'next/link';
import { ArrowRight, Cpu, Database, Layers } from 'lucide-react';

import { TickerSearch } from '@/components/ticker-search';
import { Card, CardContent } from '@/components/ui/card';

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:py-24">
      <section className="flex flex-col items-center text-center">
        <span className="rounded-full border border-[color:var(--color-border)] px-3 py-1 text-xs text-[color:var(--color-muted-foreground)]">
          Educational engineering demo · Indian equities (NSE / BSE)
        </span>
        <h1 className="mt-6 max-w-2xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          Multi-agent fundamental analysis, evidence-linked.
        </h1>
        <p className="mt-5 max-w-xl text-pretty text-[color:var(--color-muted-foreground)]">
          Type a ticker. Watch four specialised agents pull financials, valuation history,
          management commentary, and risk disclosures in parallel, then synthesise a bull/bear
          thesis where every point cites a specific finding.
        </p>

        <div className="mt-10 w-full">
          <TickerSearch autoFocus />
        </div>

        <p className="mt-3 text-xs text-[color:var(--color-muted-foreground)]">
          Try{' '}
          {['RELIANCE', 'INFY', 'HDFCBANK', 'TCS'].map((t, i) => (
            <span key={t}>
              <Link
                href={`/analyze/${t}`}
                className="underline-offset-2 hover:text-[color:var(--color-foreground)] hover:underline"
              >
                {t}
              </Link>
              {i < 3 ? ', ' : ''}
            </span>
          ))}
        </p>
      </section>

      <section className="mt-24 grid gap-4 sm:grid-cols-3">
        <FeatureCard
          icon={<Cpu className="size-5" />}
          title="Orchestration as code"
          body="The agent graph is just an asyncio.gather call you can read in 30 seconds. No graph DSL. PydanticAI does the typing."
        />
        <FeatureCard
          icon={<Layers className="size-5" />}
          title="Evidence over narrative"
          body="Every claim cites a specific value, year, or quote. Generic vocabulary ('strong', 'robust', 'attractive') is structurally rejected."
        />
        <FeatureCard
          icon={<Database className="size-5" />}
          title="Polite by design"
          body="yfinance, Screener.in (rate-limited 1/3s, robots.txt-aware), annual-report PDFs cached on disk indefinitely."
        />
      </section>

      <section className="mt-16 flex flex-col items-center gap-2 text-sm text-[color:var(--color-muted-foreground)]">
        <Link
          href="/about"
          className="inline-flex items-center gap-1 hover:text-[color:var(--color-foreground)] transition-colors"
        >
          How it works
          <ArrowRight className="size-3.5" />
        </Link>
      </section>
    </div>
  );
}

function FeatureCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-2 inline-flex size-8 items-center justify-center rounded-md bg-[color:var(--color-muted)] text-[color:var(--color-accent)]">
          {icon}
        </div>
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">{body}</p>
      </CardContent>
    </Card>
  );
}
