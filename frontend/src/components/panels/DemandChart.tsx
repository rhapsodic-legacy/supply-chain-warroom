import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Card } from '../shared/Card';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useDemand } from '../../hooks/useDemand';

interface ChartDataPoint {
  date: string;
  label: string;
  forecast: number;
  actual: number | null;
}

function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function DemandChart({ className }: { className?: string }) {
  const { data: signals, isLoading, error } = useDemand();

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!signals) return [];

    // Aggregate by date: sum forecast and actual across all products/regions
    const byDate = new Map<string, { forecast: number; actual: number | null }>();
    for (const s of signals) {
      const existing = byDate.get(s.signal_date);
      if (existing) {
        existing.forecast += s.forecast_qty;
        if (s.actual_qty != null) {
          existing.actual = (existing.actual ?? 0) + s.actual_qty;
        }
      } else {
        byDate.set(s.signal_date, {
          forecast: s.forecast_qty,
          actual: s.actual_qty != null ? s.actual_qty : null,
        });
      }
    }

    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({
        date,
        label: formatDate(date),
        forecast: vals.forecast,
        actual: vals.actual,
      }));
  }, [signals]);

  // Find the dividing line between historical and forecast-only
  const todayLabel = useMemo(() => {
    const lastActual = chartData.filter((d) => d.actual != null).pop();
    return lastActual?.label ?? null;
  }, [chartData]);

  if (isLoading) return <LoadingSpinner label="Loading demand data..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!chartData.length) return <EmptyState message="No demand signals" />;

  return (
    <Card className={className} title="Demand vs Forecast">
      <div className="flex items-center gap-4 mb-3">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'var(--wr-cyan)' }} />
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
            Forecast
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'var(--wr-green)' }} />
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
            Actual
          </span>
        </div>
        {todayLabel && (
          <span className="text-[10px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
            Historical through {todayLabel}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="gradForecast" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#58a6ff" stopOpacity={0.4} />
              <stop offset="60%" stopColor="#58a6ff" stopOpacity={0.1} />
              <stop offset="100%" stopColor="#58a6ff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradActual" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3fb950" stopOpacity={0.35} />
              <stop offset="60%" stopColor="#3fb950" stopOpacity={0.08} />
              <stop offset="100%" stopColor="#3fb950" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1a2332"
            strokeOpacity={0.6}
            vertical={false}
          />

          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={{ stroke: '#1a2332' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : String(v)}
          />

          <Tooltip
            contentStyle={{
              background: 'var(--wr-bg-elevated)',
              border: '1px solid var(--wr-border-active)',
              borderRadius: 'var(--wr-radius)',
              fontSize: 12,
              color: 'var(--wr-text-primary)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
              fontFamily: 'var(--wr-font-mono)',
            }}
            labelStyle={{ color: 'var(--wr-text-secondary)', marginBottom: 4 }}
            formatter={(value, name) => {
              const label = name === 'forecast' ? 'Forecast' : 'Actual';
              if (value == null) return ['N/A', label];
              return [Number(value).toLocaleString(), label];
            }}
            cursor={{ stroke: 'var(--wr-border-active)', strokeWidth: 1, strokeDasharray: '4 4' }}
          />

          <Area
            type="monotone"
            dataKey="forecast"
            stroke="#58a6ff"
            strokeWidth={2}
            fill="url(#gradForecast)"
            dot={false}
            activeDot={{ r: 4, fill: '#58a6ff', stroke: 'var(--wr-bg-surface)' }}
          />

          <Area
            type="monotone"
            dataKey="actual"
            stroke="#3fb950"
            strokeWidth={2}
            fill="url(#gradActual)"
            dot={false}
            activeDot={{ r: 4, fill: '#3fb950', stroke: 'var(--wr-bg-surface)' }}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
