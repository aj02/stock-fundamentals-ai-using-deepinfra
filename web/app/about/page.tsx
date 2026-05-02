import Link from 'next/link';

import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export const metadata = {
  title: 'About · fundamentals-ai',
};

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">About fundamentals-ai</h1>
      <p className="mt-2 text-sm text-[color:var(--color-muted-foreground)]">
        A public showcase of multi-agent fundamental analysis for Indian equities, built with PydanticAI.
      </p>

      <Card className="mt-6 border-[color:var(--color-warning)]/30 bg-[color:var(--color-warning)]/5">
        <CardContent className="p-5 text-sm leading-relaxed">
          <p className="font-medium">Disclaimer.</p>
          <p className="mt-2">
            This project is an educational and engineering demo. It is <strong>NOT investment advice</strong>{' '}
            and <strong>NOT a recommendation</strong> to buy or sell any security. The output is a structured
            summary of publicly available information for analytical study. Markets move on information this
            system does not see; the analysis can be wrong, stale, or incomplete. Do your own research and
            consult a SEBI-registered investment adviser before making any financial decision.
          </p>
        </CardContent>
      </Card>

      <Section title="What it does">
        <p>
          You enter a ticker. The Coordinator validates it on NSE/BSE, opens a run record, and fans out four
          agents in parallel via <code>asyncio.gather</code>:
        </p>
        <ul className="my-3 ml-5 list-disc space-y-1">
          <li>
            <strong>Financials Agent</strong> — 5-year statements, ratios, evidence-linked qualitative assessment.
          </li>
          <li>
            <strong>Valuation Agent</strong> — current multiples vs 5-year median vs peer median.
          </li>
          <li>
            <strong>Management Agent</strong> — MD&amp;A + governance extracts from the latest annual report.
          </li>
          <li>
            <strong>Risk Agent</strong> — categorised, severity-tagged risks with explicit citations.
          </li>
        </ul>
        <p>
          Once the four return, the <strong>Thesis Agent</strong> synthesises a bull case, bear case, and
          neutral summary — every point cites which prior-agent finding it derives from.
        </p>
      </Section>

      <Section title="Why PydanticAI (not LangChain / LangGraph)">
        <p>
          The orchestration is a 30-line async function. No graph DSL, no state machine to draw — just
          Python you can step through in a debugger. PydanticAI provides typed deps, typed result models, and{' '}
          <code>@agent.tool</code> decorators that bind validated tool I/O.
        </p>
      </Section>

      <Section title="Anti-generic strategy">
        <p>Three layers prevent vague output:</p>
        <ol className="my-3 ml-5 list-decimal space-y-1">
          <li>
            <strong>Schema-level</strong>: Pydantic rejects empty evidence lists and short claim strings.
            A finding without a year + value pair fails validation.
          </li>
          <li>
            <strong>Prompt-level</strong>: each agent&rsquo;s system prompt names banned vocabulary
            (&ldquo;strong&rdquo;, &ldquo;robust&rdquo;, &ldquo;market leader&rdquo;), shows good/bad
            examples, and forbids buy/sell language.
          </li>
          <li>
            <strong>Architectural</strong>: ratios are computed in Python and overlaid post-LLM, so the
            LLM is responsible only for interpretation — it cannot drift on the numbers themselves.
          </li>
        </ol>
      </Section>

      <Section title="Data sources & ethics">
        <ul className="my-3 ml-5 list-disc space-y-1">
          <li>
            <strong>yfinance</strong> — prices and basic financials.
          </li>
          <li>
            <strong>Screener.in</strong> — supplementary financials and concerns. The scraper sets a clearly
            identifying User-Agent, is rate-limited to 1 request per 3 seconds, respects robots.txt, and
            caches aggressively (24h).
          </li>
          <li>
            <strong>Annual reports</strong> — fetched directly from BSE / NSE via Screener&rsquo;s discovery,
            cached on disk indefinitely, parsed locally with pypdf.
          </li>
        </ul>
        <p>
          If scraping fails, the agent receives <code>available: false</code> and degrades gracefully — the
          run continues with partial data and the missing section is marked <code>unavailable</code> in the
          final report.
        </p>
      </Section>

      <Section title="What this is NOT">
        <ul className="my-3 ml-5 list-disc space-y-1">
          <li>Not investment advice; no buy/sell signals; no price targets; no &ldquo;score out of 10.&rdquo;</li>
          <li>No portfolio tracking, watchlist, paper trading, user accounts, or auth.</li>
          <li>No news/sentiment, options, or insider-trading data.</li>
          <li>No multi-ticker comparison — one ticker per analysis.</li>
          <li>No follow-up chat. Strict scope by design.</li>
        </ul>
      </Section>

      <Separator className="my-8" />
      <p className="text-sm text-[color:var(--color-muted-foreground)]">
        See the README and ARCHITECTURE.md in the{' '}
        <a
          href="https://github.com/your-org/fundamentals-ai"
          target="_blank"
          rel="noreferrer"
          className="underline-offset-2 hover:underline"
        >
          repository
        </a>{' '}
        for the deep technical detail.
      </p>
      <p className="mt-4 text-sm">
        <Link href="/" className="underline-offset-2 hover:underline">
          ← Back to search
        </Link>
      </p>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-[color:var(--color-foreground)]">
        {children}
      </div>
    </section>
  );
}
