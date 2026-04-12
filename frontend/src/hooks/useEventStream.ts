import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardStore } from '../stores/dashboardStore';
import { useDemoStore } from '../stores/demoStore';
import type { StreamEvent, Notification, TransportKind } from '../types/api';

let idCounter = 0;
function makeId() {
  return `evt-${Date.now()}-${++idCounter}`;
}

/** Shared WebSocket ref for bidirectional messaging from anywhere in the app. */
let _ws: WebSocket | null = null;

/**
 * Send a message to the backend via WebSocket.
 * Returns false if WebSocket is not connected (caller can fall back to REST).
 */
export function sendWsMessage(action: string, data: Record<string, unknown> = {}): boolean {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify({ action, ...data }));
    return true;
  }
  return false;
}

/** Current transport kind — useful for UI indicators. */
let _transport: TransportKind = 'sse';
export function getTransport(): TransportKind {
  return _transport;
}

export function useEventStream() {
  const qc = useQueryClient();
  const addNotification = useDashboardStore((s) => s.addNotification);
  const wsRef = useRef<WebSocket | null>(null);
  const sseRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const handleParsed = useCallback(
    (parsed: StreamEvent) => {
      handleEvent(parsed, qc, addNotification);
    },
    [qc, addNotification],
  );

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_URL || '';

    // ── Helpers ────────────────────────────────────────────
    function cleanup() {
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
        _ws = null;
      }
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    }

    function onMessage(raw: string) {
      try {
        const parsed: StreamEvent = JSON.parse(raw);
        handleParsed(parsed);
      } catch {
        // ignore malformed messages
      }
    }

    // ── SSE fallback ──────────────────────────────────────
    function connectSSE() {
      cleanup();
      _transport = 'sse';
      const url = `${baseUrl}/api/v1/stream`;
      const source = new EventSource(url);
      sseRef.current = source;

      source.onmessage = (event) => onMessage(event.data);

      source.onerror = () => {
        console.warn('[SSE] Connection lost, reconnecting...');
      };
    }

    // ── WebSocket primary ─────────────────────────────────
    function connectWS() {
      cleanup();

      // Derive WS URL from the HTTP base
      const wsBase = baseUrl
        ? baseUrl.replace(/^http/, 'ws')
        : `ws://${window.location.host}`;
      const url = `${wsBase}/api/v1/ws`;

      const ws = new WebSocket(url);
      wsRef.current = ws;
      _ws = ws;

      ws.onopen = () => {
        _transport = 'websocket';
        console.info('[WS] Connected');
      };

      ws.onmessage = (event) => onMessage(event.data);

      ws.onclose = (event) => {
        _ws = null;
        if (event.code === 1000) return; // clean close on unmount

        console.warn('[WS] Connection lost, falling back to SSE');
        connectSSE();
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — SSE fallback happens there
      };
    }

    // Start with WebSocket
    connectWS();

    return cleanup;
  }, [handleParsed]);
}

function handleEvent(
  event: StreamEvent,
  qc: ReturnType<typeof useQueryClient>,
  addNotification: (n: Notification) => void,
) {
  switch (event.type) {
    case 'risk_update':
      qc.invalidateQueries({ queryKey: ['risk-events'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      addNotification({
        id: makeId(),
        type: 'risk',
        severity: (event.data.severity as Notification['severity']) || 'medium',
        title: (event.data.title as string) || 'Risk Update',
        message: (event.data.description as string) || 'A risk event has been updated.',
        timestamp: event.timestamp,
        read: false,
      });
      break;

    case 'order_update':
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      break;

    case 'agent_action':
      qc.invalidateQueries({ queryKey: ['agent-decisions'] });
      addNotification({
        id: makeId(),
        type: 'agent',
        severity: 'info',
        title: 'Agent Action',
        message: (event.data.action as string) || 'An agent took an action.',
        timestamp: event.timestamp,
        read: false,
      });
      break;

    case 'agent_handoff':
      qc.invalidateQueries({ queryKey: ['agent-handoff-sessions'] });
      break;

    case 'supply_alert':
      qc.invalidateQueries({ queryKey: ['dashboard', 'supply-health'] });
      addNotification({
        id: makeId(),
        type: 'system',
        severity: (event.data.severity as Notification['severity']) || 'high',
        title: 'Supply Alert',
        message: (event.data.message as string) || 'Supply chain alert detected.',
        timestamp: event.timestamp,
        read: false,
      });
      break;

    case 'demo_step': {
      const { setStep } = useDemoStore.getState();
      setStep(
        event.data.step as string,
        (event.data.panel as string) || null,
        (event.data.step_index as number) ?? 0,
        (event.data.total_steps as number) ?? 9,
        event.data,
      );
      break;
    }

    case 'connected':
      console.info('[WS] Server confirmed:', event.data);
      break;

    case 'heartbeat':
    case 'pong':
    case 'filter_ack':
    case 'error':
      // no-op for UI — handled internally
      break;
  }
}
