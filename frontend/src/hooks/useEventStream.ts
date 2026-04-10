import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDashboardStore } from '../stores/dashboardStore';
import { useDemoStore } from '../stores/demoStore';
import type { StreamEvent, Notification } from '../types/api';

let idCounter = 0;
function makeId() {
  return `sse-${Date.now()}-${++idCounter}`;
}

export function useEventStream() {
  const qc = useQueryClient();
  const addNotification = useDashboardStore((s) => s.addNotification);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    const url = `${baseUrl}/api/v1/stream`;

    const source = new EventSource(url);
    sourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const parsed: StreamEvent = JSON.parse(event.data);
        handleEvent(parsed, qc, addNotification);
      } catch {
        // ignore malformed messages
      }
    };

    source.onerror = () => {
      // EventSource reconnects automatically
      console.warn('[SSE] Connection lost, reconnecting...');
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [qc, addNotification]);
}

function handleEvent(
  event: StreamEvent,
  qc: ReturnType<typeof useQueryClient>,
  addNotification: (n: Notification) => void
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

    case 'heartbeat':
      // no-op
      break;
  }
}
