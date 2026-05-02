'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Search, Loader2 } from 'lucide-react';

import { searchTickers } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function TickerSearch({ autoFocus = false }: { autoFocus?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = React.useState('');
  const [open, setOpen] = React.useState(false);
  const [highlight, setHighlight] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const { data, isFetching } = useQuery({
    queryKey: ['tickers', query],
    queryFn: () => searchTickers(query),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  const results = data?.results ?? [];

  const submit = React.useCallback(
    (ticker: string) => {
      const t = ticker.trim().toUpperCase();
      if (!t) return;
      setOpen(false);
      router.push(`/analyze/${encodeURIComponent(t)}`);
    },
    [router]
  );

  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === 'ArrowDown') {
      setHighlight((h) => Math.min(h + 1, results.length - 1));
      e.preventDefault();
    } else if (e.key === 'ArrowUp') {
      setHighlight((h) => Math.max(h - 1, 0));
      e.preventDefault();
    } else if (e.key === 'Enter') {
      const picked = results[highlight];
      submit(picked ? picked.ticker : query);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="relative w-full max-w-xl">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[color:var(--color-muted-foreground)]" />
          <Input
            ref={inputRef}
            autoFocus={autoFocus}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              setHighlight(0);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={onKeyDown}
            placeholder="Search a ticker — e.g. RELIANCE, INFY, HDFCBANK"
            className="h-12 pl-9 text-base"
            aria-autocomplete="list"
            aria-expanded={open}
            spellCheck={false}
          />
          {isFetching && (
            <Loader2 className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-[color:var(--color-muted-foreground)]" />
          )}
        </div>
        <Button size="lg" onClick={() => submit(query)} disabled={!query.trim()}>
          Analyze
        </Button>
      </div>

      {open && results.length > 0 && (
        <div
          role="listbox"
          className="absolute z-50 mt-2 w-full overflow-hidden rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-card)] shadow-lg"
        >
          {results.map((r, i) => (
            <button
              key={r.ticker}
              role="option"
              aria-selected={i === highlight}
              onMouseEnter={() => setHighlight(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                submit(r.ticker);
              }}
              className={cn(
                'flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition-colors',
                i === highlight
                  ? 'bg-[color:var(--color-muted)]'
                  : 'hover:bg-[color:var(--color-muted)]'
              )}
            >
              <div>
                <div className="font-medium">{r.ticker}</div>
                <div className="text-xs text-[color:var(--color-muted-foreground)]">{r.name}</div>
              </div>
              <span className="rounded-full bg-[color:var(--color-muted)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[color:var(--color-muted-foreground)]">
                {r.sector}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
