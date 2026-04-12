import { useState, useEffect } from 'react';
import { useOverview } from '../../hooks/useDashboard';
import { getTransport } from '../../hooks/useEventStream';
import type { TransportKind } from '../../types/api';

export function StatusBar() {
  const { data } = useOverview();
  const [transport, setTransport] = useState<TransportKind>(getTransport());

  useEffect(() => {
    const id = setInterval(() => setTransport(getTransport()), 2000);
    return () => clearInterval(id);
  }, []);

  const items = [
    { label: 'ACTIVE RISKS', value: data?.active_risk_events ?? '--', severity: 'red' },
    { label: 'CRITICAL RISKS', value: data?.critical_risk_events ?? '--', severity: 'red' },
    { label: 'ORDERS', value: data?.active_orders ?? '--', severity: 'cyan' },
    { label: 'TOTAL ORDERS', value: data?.total_orders ?? '--', severity: 'cyan' },
    { label: 'FILL RATE', value: data ? `${data.avg_fill_rate.toFixed(1)}%` : '--%', severity: 'green' },
    { label: 'REVENUE', value: data ? `$${(data.total_revenue / 1_000_000).toFixed(1)}M` : '--', severity: 'amber' },
    { label: 'SUPPLIERS', value: data?.total_suppliers ?? '--', severity: 'green' },
    { label: 'ACTIVE SUPPLIERS', value: data?.active_suppliers ?? '--', severity: 'green' },
  ];

  const colorMap: Record<string, string> = {
    red: 'var(--wr-red)',
    green: 'var(--wr-green)',
    amber: 'var(--wr-amber)',
    cyan: 'var(--wr-cyan)',
  };

  // Duplicate for seamless scroll
  const tickerItems = [...items, ...items];

  return (
    <div className="status-bar-gradient overflow-hidden flex items-center" style={{ height: '32px' }}>
      <div
        className="flex-shrink-0 flex items-center gap-1 px-3 border-r"
        style={{ borderColor: 'var(--wr-border)' }}
        title={`Real-time: ${transport === 'websocket' ? 'WebSocket' : 'SSE fallback'}`}
      >
        <span
          className="inline-block w-1.5 h-1.5 rounded-full"
          style={{
            backgroundColor: transport === 'websocket' ? 'var(--wr-green)' : 'var(--wr-amber)',
            boxShadow: `0 0 4px ${transport === 'websocket' ? 'var(--wr-green)' : 'var(--wr-amber)'}`,
          }}
        />
        <span
          className="text-[9px] font-mono-numbers font-semibold uppercase tracking-wider"
          style={{ color: 'var(--wr-text-muted)' }}
        >
          {transport === 'websocket' ? 'WS' : 'SSE'}
        </span>
      </div>
      <div className="ticker-scroll h-full items-center flex-1 overflow-hidden">
        {tickerItems.map((item, i) => (
          <div key={i} className="flex items-center gap-2 flex-shrink-0">
            <span
              className="text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--wr-text-muted)' }}
            >
              {item.label}
            </span>
            <span
              className="font-mono-numbers text-xs font-bold"
              style={{ color: colorMap[item.severity] }}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
