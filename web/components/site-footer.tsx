import { DisclaimerBanner } from '@/components/disclaimer';

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-[color:var(--color-border)]">
      <DisclaimerBanner />
      <div className="mx-auto max-w-7xl px-4 py-6 text-xs text-[color:var(--color-muted-foreground)]">
        <p>
          fundamentals-ai is a public showcase of multi-agent fundamental analysis built with
          PydanticAI, FastAPI, and Next.js. See the README in the repository for more.
        </p>
      </div>
    </footer>
  );
}
