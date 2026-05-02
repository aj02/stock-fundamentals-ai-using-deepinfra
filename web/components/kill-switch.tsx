'use client';

import * as React from 'react';
import { useMutation } from '@tanstack/react-query';
import { OctagonX } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cancelAllRuns } from '@/lib/api';

/**
 * Site-wide kill switch. Lives in the header so the user can stop ALL
 * in-flight LLM runs instantly — no need to navigate back to the page
 * that started them.
 */
export function KillSwitch() {
  const cancelAll = useMutation({ mutationFn: () => cancelAllRuns() });
  const justRan = cancelAll.data;
  const count = justRan?.cancelled.length;

  // Show a one-shot banner of what got cancelled.
  React.useEffect(() => {
    if (justRan) {
      const id = setTimeout(() => cancelAll.reset(), 4000);
      return () => clearTimeout(id);
    }
  }, [justRan, cancelAll]);

  return (
    <div className="flex items-center gap-2">
      {justRan != null && (
        <span className="text-xs text-[color:var(--color-muted-foreground)]">
          {count === 0 ? 'no active runs' : `cancelled ${count}`}
        </span>
      )}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => cancelAll.mutate()}
        disabled={cancelAll.isPending}
        aria-label="Cancel all in-flight analyses"
        title="Stop every in-flight analysis (kill switch)"
      >
        <OctagonX className="size-3.5" />
        <span className="hidden sm:inline">{cancelAll.isPending ? 'Stopping…' : 'Stop all'}</span>
      </Button>
    </div>
  );
}
