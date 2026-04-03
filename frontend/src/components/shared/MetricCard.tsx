interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  severity?: 'critical' | 'warning' | 'safe' | 'neutral';
  className?: string;
}

const trendArrows: Record<string, string> = {
  up: '\u2191',
  down: '\u2193',
  flat: '\u2192',
};

const severityColors: Record<string, string> = {
  critical: 'var(--wr-red)',
  warning: 'var(--wr-amber)',
  safe: 'var(--wr-green)',
  neutral: 'var(--wr-cyan)',
};

export function MetricCard({
  label,
  value,
  trend,
  trendValue,
  severity = 'neutral',
  className = '',
}: MetricCardProps) {
  const color = severityColors[severity];

  return (
    <div className={`war-room-card p-4 ${className}`}>
      <p
        className="text-xs font-semibold uppercase tracking-wider mb-2"
        style={{ color: 'var(--wr-text-muted)' }}
      >
        {label}
      </p>
      <p className="font-mono-numbers text-3xl font-bold leading-none" style={{ color }}>
        {value}
      </p>
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          <span
            className="font-mono-numbers text-sm font-semibold"
            style={{
              color:
                trend === 'up'
                  ? severity === 'critical'
                    ? 'var(--wr-red)'
                    : 'var(--wr-green)'
                  : trend === 'down'
                    ? severity === 'critical'
                      ? 'var(--wr-green)'
                      : 'var(--wr-red)'
                    : 'var(--wr-text-muted)',
            }}
          >
            {trendArrows[trend]} {trendValue}
          </span>
        </div>
      )}
    </div>
  );
}
