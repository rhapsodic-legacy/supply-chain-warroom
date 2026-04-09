import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useRiskEvents } from '../../hooks/useRiskEvents';


function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const eventTypeIcons: Record<string, string> = {
  geopolitical: 'GEO',
  weather: 'WX',
  supplier: 'SUP',
  logistics: 'LOG',
  demand: 'DMD',
  cyber: 'CYB',
  regulatory: 'REG',
};

export function RiskFeed({ className }: { className?: string }) {
  const { data: events, isLoading, error } = useRiskEvents(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const PREVIEW_COUNT = 4;

  if (isLoading) return <LoadingSpinner label="Scanning threats..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!events?.length) return <EmptyState message="No active risk events" />;

  const sorted = [...events].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );

  const visible = showAll ? sorted : sorted.slice(0, PREVIEW_COUNT);
  const hiddenCount = sorted.length - PREVIEW_COUNT;

  return (
    <Card className={className} title="Risk Feed" badge={<Badge severity="critical" dot>{events.length} Active</Badge>}>
      <div className="space-y-2 flex-1 overflow-y-auto pr-1" style={{ minHeight: 0 }}>
        {visible.map((event) => {
          const isExpanded = expandedId === event.id;
          const isCritical = event.severity === 'critical';

          return (
            <div
              key={event.id}
              className={`rounded-lg p-3 cursor-pointer transition-all duration-200 ${
                isCritical && event.is_active ? 'pulse-alert' : ''
              } ${
                event.is_active ? 'glow-critical' : ''
              }`}
              style={{
                background: 'var(--wr-bg-elevated)',
                border: '1px solid var(--wr-border)',
              }}
              onClick={() => setExpandedId(isExpanded ? null : event.id)}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <Badge severity={event.severity as 'critical' | 'high' | 'medium' | 'low'} dot={isCritical}>
                    {event.severity}
                  </Badge>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[10px] font-mono-numbers font-semibold px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--wr-cyan-dim)',
                        color: 'var(--wr-cyan)',
                      }}
                    >
                      {eventTypeIcons[event.event_type] ?? event.event_type.slice(0, 3).toUpperCase()}
                    </span>
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--wr-text-primary)' }}>
                      {event.title}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs" style={{ color: 'var(--wr-text-muted)' }}>
                      {timeAgo(event.started_at)}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--wr-text-secondary)' }}>
                      {event.affected_region ?? ''}
                    </span>
                  </div>
                </div>
                <span
                  className="text-xs flex-shrink-0"
                  style={{ color: 'var(--wr-text-muted)' }}
                >
                  {isExpanded ? '\u25B2' : '\u25BC'}
                </span>
              </div>

              {isExpanded && (
                <div className="mt-3 pt-3 animate-fade-in" style={{ borderTop: '1px solid var(--wr-border)' }}>
                  <p className="text-xs leading-relaxed mb-2" style={{ color: 'var(--wr-text-secondary)' }}>
                    {event.description}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <span className="text-[10px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
                      Severity Score: <span style={{ color: 'var(--wr-amber)' }}>{(event.severity_score * 100).toFixed(0)}%</span>
                    </span>
                  </div>
                  {event.impacts.length > 0 && (
                    <div className="mt-2">
                      <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
                        Impacts
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {event.impacts.map((impact) => (
                          <span
                            key={impact.id}
                            className="text-[10px] font-mono-numbers px-1.5 py-0.5 rounded"
                            style={{
                              background: impact.entity_type === 'supplier' ? 'var(--wr-red-dim)' : 'var(--wr-amber-dim)',
                              color: impact.entity_type === 'supplier' ? 'var(--wr-red)' : 'var(--wr-amber)',
                            }}
                          >
                            {impact.entity_name} ({impact.impact_multiplier.toFixed(1)}x)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {hiddenCount > 0 && (
          <button
            className="w-full py-2 text-[11px] font-semibold uppercase tracking-wider rounded-lg transition-all duration-200"
            style={{
              color: 'var(--wr-cyan)',
              background: 'var(--wr-cyan-dim)',
              border: '1px solid rgba(88, 166, 255, 0.2)',
            }}
            onClick={() => setShowAll(!showAll)}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(88, 166, 255, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--wr-cyan-dim)';
            }}
          >
            {showAll ? 'Show Less' : `Show ${hiddenCount} More`}
          </button>
        )}
      </div>
    </Card>
  );
}
