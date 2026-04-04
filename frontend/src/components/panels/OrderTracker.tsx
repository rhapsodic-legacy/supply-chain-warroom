import { useMemo } from 'react';
import { Card } from '../shared/Card';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useOrderStats } from '../../hooks/useOrders';

const PIPELINE_STAGES = [
  'pending',
  'confirmed',
  'in_production',
  'shipped',
  'in_transit',
  'customs',
  'delivered',
] as const;

const STAGE_LABELS: Record<string, string> = {
  pending: 'Pending',
  confirmed: 'Confirmed',
  in_production: 'In Production',
  shipped: 'Shipped',
  in_transit: 'In Transit',
  customs: 'Customs',
  delivered: 'Delivered',
  delayed: 'Delayed',
  cancelled: 'Cancelled',
};

const STAGE_COLORS: Record<string, string> = {
  pending: 'var(--wr-amber)',
  confirmed: 'var(--wr-amber)',
  in_production: 'var(--wr-purple)',
  shipped: 'var(--wr-cyan)',
  in_transit: 'var(--wr-cyan)',
  customs: 'var(--wr-amber)',
  delivered: 'var(--wr-green)',
  delayed: 'var(--wr-red)',
  cancelled: '#6e1a1a',
};

export function OrderTracker({ className }: { className?: string }) {
  const { data: stats, isLoading, error } = useOrderStats();

  const total = useMemo(() => {
    if (!stats) return 0;
    return Object.values(stats).reduce((sum, v) => sum + v, 0);
  }, [stats]);

  const maxCount = useMemo(() => {
    if (!stats) return 1;
    const vals = Object.values(stats).filter((v) => v > 0);
    return Math.max(...vals, 1);
  }, [stats]);

  if (isLoading) return <LoadingSpinner label="Loading orders..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!stats) return <EmptyState message="No order data available" />;

  const delayedCount = stats['delayed'] ?? 0;
  const cancelledCount = stats['cancelled'] ?? 0;

  return (
    <Card className={className} title="Order Pipeline">
      {/* Summary row */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-baseline gap-2">
          <span className="font-mono-numbers text-2xl font-bold" style={{ color: 'var(--wr-cyan)' }}>
            {total}
          </span>
          <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>Total Orders</span>
        </div>
        {delayedCount > 0 && (
          <div className="flex items-center gap-1.5 ml-auto">
            <span className="inline-block w-2 h-2 rounded-full pulse-dot" style={{ background: 'var(--wr-red)' }} />
            <span className="font-mono-numbers text-xs font-semibold" style={{ color: 'var(--wr-red)' }}>
              {delayedCount} delayed
            </span>
          </div>
        )}
      </div>

      {/* Pipeline visualization */}
      <div className="space-y-2">
        {PIPELINE_STAGES.map((stage, idx) => {
          const count = stats[stage] ?? 0;
          const pct = (count / maxCount) * 100;
          return (
            <div key={stage} className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 w-28 flex-shrink-0">
                <span
                  className="text-[10px] font-mono-numbers w-4 text-center"
                  style={{ color: 'var(--wr-text-muted)' }}
                >
                  {idx + 1}
                </span>
                <span className="text-xs truncate" style={{ color: 'var(--wr-text-secondary)' }}>
                  {STAGE_LABELS[stage]}
                </span>
              </div>
              <div className="flex-1 flex items-center gap-2">
                <div
                  className="h-5 rounded overflow-hidden flex-1"
                  style={{ background: 'var(--wr-bg-primary)' }}
                >
                  <div
                    className="h-full rounded transition-all duration-700 ease-out"
                    style={{
                      width: `${Math.max(pct, count > 0 ? 4 : 1)}%`,
                      background: `linear-gradient(90deg, ${STAGE_COLORS[stage]}15, ${STAGE_COLORS[stage]}30)`,
                      borderRight: count > 0 ? `2px solid ${STAGE_COLORS[stage]}` : 'none',
                      boxShadow: count > 0 ? `inset 0 0 8px ${STAGE_COLORS[stage]}10` : 'none',
                    }}
                  />
                </div>
                <span
                  className="font-mono-numbers text-xs font-semibold w-8 text-right"
                  style={{ color: STAGE_COLORS[stage] }}
                >
                  {count}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Delayed and Cancelled */}
      {(delayedCount > 0 || cancelledCount > 0) && (
        <div
          className="flex items-center gap-4 mt-4 pt-3"
          style={{ borderTop: '1px solid var(--wr-border)' }}
        >
          {delayedCount > 0 && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: 'var(--wr-red-dim)', border: '1px solid rgba(248, 81, 73, 0.3)' }}
            >
              <span className="inline-block w-2 h-2 rounded-full pulse-dot" style={{ background: 'var(--wr-red)' }} />
              <span className="text-xs font-semibold" style={{ color: 'var(--wr-red)' }}>
                Delayed
              </span>
              <span className="font-mono-numbers text-sm font-bold" style={{ color: 'var(--wr-red)' }}>
                {delayedCount}
              </span>
            </div>
          )}
          {cancelledCount > 0 && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: 'var(--wr-red-dim)', border: '1px solid rgba(248, 81, 73, 0.3)' }}
            >
              <span className="text-xs font-semibold" style={{ color: 'var(--wr-red)' }}>
                Cancelled
              </span>
              <span className="font-mono-numbers text-sm font-bold" style={{ color: 'var(--wr-red)' }}>
                {cancelledCount}
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
