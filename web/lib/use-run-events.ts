/**
 * useRunEvents — subscribes to /ws/runs/{run_id} and exposes a typed
 * stream of run events plus connection state.
 *
 * Events are appended in arrival order. Reconnection is intentionally
 * disabled — if the server closes the WS the run is over (or crashed)
 * and the page should fall back to polling /runs/{run_id}.
 */

'use client';

import { useEffect, useRef, useState } from 'react';

import { runEventSchema, type RunEvent } from './schema';
import { wsBase } from './api';

export type WsState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

export interface UseRunEventsResult {
  events: RunEvent[];
  state: WsState;
  closedReason?: string;
}

export function useRunEvents(runId: string | null): UseRunEventsResult {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [state, setState] = useState<WsState>('idle');
  const [closedReason, setClosedReason] = useState<string | undefined>();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) {
      setState('idle');
      return;
    }
    setEvents([]);
    setState('connecting');

    const url = `${wsBase()}/ws/runs/${runId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setState('open');
    ws.onmessage = (msg) => {
      try {
        const parsed = runEventSchema.parse(JSON.parse(msg.data as string));
        setEvents((prev) => [...prev, parsed]);
      } catch (err) {
        console.warn('useRunEvents: dropped malformed event', err);
      }
    };
    ws.onerror = () => setState('error');
    ws.onclose = (ev) => {
      setState('closed');
      setClosedReason(ev.reason || `code ${ev.code}`);
    };

    return () => {
      // 1000 = normal closure
      try { ws.close(1000, 'page unmounted'); } catch { /* noop */ }
      wsRef.current = null;
    };
  }, [runId]);

  return { events, state, closedReason };
}
