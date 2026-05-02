import Link from 'next/link';

import { KillSwitch } from '@/components/kill-switch';
import { ThemeToggle } from '@/components/theme-toggle';

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-[color:var(--color-border)] bg-[color:var(--color-background)]/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="size-2 rounded-full bg-[color:var(--color-accent)]" aria-hidden />
          <span className="font-semibold tracking-tight">fundamentals-ai</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link
            href="/about"
            className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)] transition-colors"
          >
            About
          </Link>
          <a
            href="https://github.com/your-org/fundamentals-ai"
            target="_blank"
            rel="noreferrer"
            className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)] transition-colors"
          >
            GitHub
          </a>
          <KillSwitch />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
