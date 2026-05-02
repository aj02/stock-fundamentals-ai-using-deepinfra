'use client';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, Loader2, RefreshCw, X } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AgentActivityPanel } from '@/components/agent-activity-panel';
import { ReportTabs } from '@/components/report/report-tabs';
import { useRunEvents } from '@/lib/use-run-events';
import { cancelRun, fetchRun, startAnalysis, APIError } from '@/lib/api';

export default function AnalyzeTickerPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = React.use(params);
  const tickerU = decodeURIComponent(ticker).toUpperCase();

  const startMutation = useMutation({
    mutationFn: (forceRefresh: boolean) =>
      startAnalysis(tickerU, { depth: 'full', forceRefresh }),
  });
  const cancelMutation = useMutation({
    mutationFn: (runId: string) => cancelRun(runId),
  });

  // Auto-kick the analysis on mount with cache-first behaviour.
  React.useEffect(() => {
    startMutation.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickerU]);

  const runId = startMutation.data?.run_id ?? null;
  const wasCached = startMutation.data?.cached ?? false;

  // Only stream WS events if this is a fresh run; cached runs are already done.
  const wsRunId = wasCached ? null : runId;
  const { events, state: wsState, closedReason } = useRunEvents(wsRunId);

  // Pull the persisted RunReport once available (immediately for cached, after
  // WS closes for fresh runs).
  const reportQuery = useQuery({
    queryKey: ['run', runId, wsState, wasCached],
    queryFn: () => fetchRun(runId!),
    enabled: !!runId && (wasCached || wsState === 'closed'),
    refetchInterval: (q) =>
      // Poll until report is materialised. For cached, it's immediate.
      (q.state.data || q.state.error) ? false : 1500,
    retry: 8,
  });

  const refresh = () => {
    cancelMutation.reset();
    startMutation.mutate(true);
  };

  const cancel = () => {
    if (runId) cancelMutation.mutate(runId);
  };

  const isRunning = !wasCached && (wsState === 'connecting' || wsState === 'open');

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]"
        >
          <ArrowLeft className="size-3.5" /> Search
        </Link>
        {reportQuery.data?.run_id && (
          <Link
            href={`/report/${reportQuery.data.run_id}`}
            className="inline-flex items-center gap-1 text-xs text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]"
          >
            Shareable report URL <ExternalLink className="size-3" />
          </Link>
        )}
      </div>

      <header className="mb-6 flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className="font-mono text-3xl font-semibold tracking-tight">{tickerU}</h1>
          <p className="text-sm text-[color:var(--color-muted-foreground)]">
            {startMutation.isPending && 'Looking up cached analysis…'}
            {wasCached && reportQuery.data && (
              <>
                Showing cached analysis from{' '}
                {reportQuery.data.report.completed_at
                  ? new Date(reportQuery.data.report.completed_at).toLocaleString('en-IN')
                  : 'earlier'}
                . Click <strong>Refresh</strong> to re-run.
              </>
            )}
            {wsState === 'connecting' && !wasCached && 'Starting analysis…'}
            {wsState === 'open' && 'Streaming agent events…'}
            {wsState === 'closed' && !wasCached && (reportQuery.data ? 'Run complete.' : 'Loading final report…')}
            {wsState === 'error' && 'WebSocket error — falling back to polling.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {wasCached && (
            <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
              cached
            </Badge>
          )}
          {isRunning && (
            <span className="inline-flex items-center gap-1.5 text-xs text-[color:var(--color-accent)]">
              <Loader2 className="size-3 animate-spin" /> live
            </span>
          )}
          {isRunning ? (
            <Button
              variant="outline"
              size="sm"
              onClick={cancel}
              disabled={cancelMutation.isPending}
              aria-label="Cancel analysis"
            >
              <X className="size-3.5" />
              {cancelMutation.isPending ? 'Cancelling…' : 'Cancel'}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={startMutation.isPending}
            >
              <RefreshCw className="size-3.5" />
              {startMutation.isPending ? 'Refreshing…' : 'Refresh analysis'}
            </Button>
          )}
        </div>
      </header>

      {startMutation.error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Could not start analysis</AlertTitle>
          <AlertDescription>{describe(startMutation.error)}</AlertDescription>
        </Alert>
      )}
      {cancelMutation.data && cancelMutation.data.cancelled.length === 0 && (
        <Alert className="mb-4">
          <AlertDescription>
            Run was already completed before the cancel reached it. No tokens were saved.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-[300px_1fr]">
        <div className="space-y-3">
          {!wasCached && <AgentActivityPanel events={events} />}
          {wasCached && (
            <Card>
              <CardContent className="p-4 text-xs text-[color:var(--color-muted-foreground)]">
                Cached run — no agents re-ran. The full report is to the right.
              </CardContent>
            </Card>
          )}
          {wsState === 'closed' && closedReason && !wasCached && (
            <p className="text-xs text-[color:var(--color-muted-foreground)]">
              WebSocket closed · {closedReason}
            </p>
          )}
        </div>

        <div className="space-y-6">
          {reportQuery.isLoading || (!reportQuery.data && wsState !== 'closed' && !wasCached) ? (
            <ResultsSkeleton />
          ) : reportQuery.data ? (
            <ReportTabs report={reportQuery.data.report} animate={!wasCached} />
          ) : reportQuery.error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not fetch report</AlertTitle>
              <AlertDescription>{describe(reportQuery.error)}</AlertDescription>
            </Alert>
          ) : (
            <ResultsSkeleton />
          )}
        </div>
      </div>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-3 p-5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-7 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </CardContent>
      </Card>
      <Card>
        <CardContent className="space-y-3 p-5">
          <Skeleton className="h-4 w-32" />
          <div className="grid grid-cols-2 gap-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function describe(err: unknown): string {
  if (err instanceof APIError) return err.message;
  if (err instanceof Error) return err.message;
  return String(err);
}
