import { useOverview } from '../../hooks/useDashboard';

export function StatusBar() {
  const { data } = useOverview();

  const items = [
    { label: 'ACTIVE RISKS', value: data?.active_risk_events ?? '--', severity: 'red' },
    { label: 'CRITICAL RISKS', value: data?.critical_risk_events ?? '--', severity: 'red' },
    { label: 'ORDERS', value: data?.active_orders ?? '--', severity: 'cyan' },
    { label: 'TOTAL ORDERS', value: data?.total_orders ?? '--', severity: 'cyan' },
    { label: 'FILL RATE', value: data ? `${(data.avg_fill_rate * 100).toFixed(1)}%` : '--%', severity: 'green' },
    { label: 'REVENUE', value: data ? `$${(data.total_revenue / 1000).toFixed(0)}K` : '--', severity: 'amber' },
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
    <div className="status-bar-gradient overflow-hidden" style={{ height: '32px' }}>
      <div className="ticker-scroll h-full items-center">
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
