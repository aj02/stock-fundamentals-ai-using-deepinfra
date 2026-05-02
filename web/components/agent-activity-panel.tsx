'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Check, CircleAlert, Loader2, Clock } from 'lucide-react';

import type { RunEvent } from '@/lib/schema';
import { cn } from '@/lib/utils';

type AgentName = 'coordinator' | 'financials' | 'valuation' | 'management' | 'risk' | 'thesis';
type AgentStatus = 'queued' | 'running' | 'completed' | 'failed' | 'idle';

interface AgentRowState {
  status: AgentStatus;
  durationSeconds?: number;
  findingsCount?: number;
  error?: string;
  currentTool?: string;
  toolHistory: { name: string; startedAt: number; durationMs?: number }[];
}

const DEFAULT: AgentRowState = { status: 'idle', toolHistory: [] };

function reduceEvents(events: RunEvent[]): Record<AgentName, AgentRowState> {
  const acc: Record<AgentName, AgentRowState> = {
    coordinator: { ...DEFAULT },
    financials: { ...DEFAULT },
    valuation: { ...DEFAULT },
    management: { ...DEFAULT },
    risk: { ...DEFAULT },
    thesis: { ...DEFAULT },
  };
  for (const e of events) {
    const t = (e as { type: string }).type;
    const agent = (e as { agent?: AgentName }).agent;
    if (t === 'agent_queued' && agent) {
      acc[agent] = { ...acc[agent], status: 'queued' };
    } else if (t === 'agent_started' && agent) {
      acc[agent] = { ...acc[agent], status: 'running' };
    } else if (t === 'agent_completed' && agent) {
      acc[agent] = {
        ...acc[agent],
        status: 'completed',
        durationSeconds: (e as { duration_seconds?: number }).duration_seconds,
        findingsCount: (e as { findings_count?: number }).findings_count,
        currentTool: undefined,
      };
    } else if (t === 'agent_failed' && agent) {
      acc[agent] = {
        ...acc[agent],
        status: 'failed',
        error: (e as { error?: string }).error,
        currentTool: undefined,
      };
    } else if (t === 'tool_called' && agent) {
      const toolName = (e as { tool_name?: string }).tool_name ?? 'tool';
      acc[agent] = {
        ...acc[agent],
        currentTool: toolName,
        toolHistory: [...acc[agent].toolHistory, { name: toolName, startedAt: Date.now() }],
      };
    } else if (t === 'tool_completed' && agent) {
      const toolName = (e as { tool_name?: string }).tool_name ?? 'tool';
      const ms = (e as { duration_ms?: number }).duration_ms;
      const last = acc[agent].toolHistory.findLast?.((x) => x.name === toolName && x.durationMs == null);
      if (last) last.durationMs = ms;
      acc[agent] = { ...acc[agent], currentTool: undefined };
    } else if (t === 'thesis_started') {
      acc.thesis = { ...acc.thesis, status: 'running' };
    } else if (t === 'thesis_completed') {
      acc.thesis = {
        ...acc.thesis,
        status: 'completed',
        findingsCount:
          ((e as { bull_points?: number }).bull_points ?? 0) +
          ((e as { bear_points?: number }).bear_points ?? 0),
      };
    }
  }
  return acc;
}

const LABELS: Record<AgentName, string> = {
  coordinator: 'Coordinator',
  financials: 'Financials',
  valuation: 'Valuation',
  management: 'Management',
  risk: 'Risk',
  thesis: 'Thesis',
};

export function AgentActivityPanel({ events }: { events: RunEvent[] }) {
  const states = React.useMemo(() => reduceEvents(events), [events]);
  const order: AgentName[] = ['financials', 'valuation', 'management', 'risk', 'thesis'];

  return (
    <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-card)]">
      <div className="border-b border-[color:var(--color-border)] px-4 py-3">
        <h2 className="text-sm font-semibold tracking-tight">Agent activity</h2>
        <p className="text-xs text-[color:var(--color-muted-foreground)]">
          Four agents run in parallel via asyncio.gather; Thesis runs once they return.
        </p>
      </div>
      <ul className="divide-y divide-[color:var(--color-border)]">
        {order.map((agent, i) => (
          <AgentRow key={agent} agent={agent} state={states[agent]} delayMs={i * 60} />
        ))}
      </ul>
    </div>
  );
}

function AgentRow({
  agent,
  state,
  delayMs,
}: {
  agent: AgentName;
  state: AgentRowState;
  delayMs: number;
}) {
  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut', delay: delayMs / 1000 }}
      className="flex items-start gap-3 px-4 py-3"
    >
      <div className="mt-0.5 size-5 shrink-0">
        <StatusIcon status={state.status} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium">{LABELS[agent]}</span>
          {state.status === 'completed' && (
            <span className="text-xs text-[color:var(--color-muted-foreground)]">
              {state.durationSeconds?.toFixed(1)}s
              {state.findingsCount != null && ` · ${state.findingsCount} findings`}
            </span>
          )}
          {state.status === 'failed' && (
            <span className="text-xs text-[color:var(--color-negative)]">failed</span>
          )}
        </div>
        {state.status === 'running' && (
          <p className="mt-0.5 text-xs text-[color:var(--color-muted-foreground)]">
            {state.currentTool
              ? <>calling <span className="font-mono">{state.currentTool}</span>…</>
              : 'thinking…'}
          </p>
        )}
        {state.status === 'failed' && state.error && (
          <p className="mt-0.5 line-clamp-2 text-xs text-[color:var(--color-negative)]">{state.error}</p>
        )}
        {state.toolHistory.length > 0 && state.status === 'completed' && (
          <p className="mt-0.5 text-xs text-[color:var(--color-muted-foreground)]">
            tools: {state.toolHistory.map((t) => t.name).join(' · ')}
          </p>
        )}
      </div>
    </motion.li>
  );
}

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === 'running') {
    return <Loader2 className="size-5 animate-spin text-[color:var(--color-accent)]" />;
  }
  if (status === 'completed') {
    return <Check className={cn('size-5 text-[color:var(--color-positive)]')} />;
  }
  if (status === 'failed') {
    return <CircleAlert className="size-5 text-[color:var(--color-negative)]" />;
  }
  if (status === 'queued') {
    return <Clock className="size-5 text-[color:var(--color-muted-foreground)]" />;
  }
  return <div className="size-3 rounded-full border border-[color:var(--color-border)]" aria-hidden />;
}
