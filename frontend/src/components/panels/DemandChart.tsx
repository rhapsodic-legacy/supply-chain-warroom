import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { Card } from '../shared/Card';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useDemand } from '../../hooks/useDemand';
import type { DemandSignal } from '../../types/api';

interface ChartDataPoint {
  date: string;
  label: string;
  forecast: number;
  actual: number;
  variance: number;
  overThreshold: boolean;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function DemandChart({ className }: { className?: string }) {
  const { data: signals, isLoading, error } = useDemand();

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!signals) return [];
    return [...signals]
      .sort((a, b) => new Date(a.signal_date).getTime() - new Date(b.signal_date).getTime())
      .map((s: DemandSignal) => ({
        date: s.signal_date,
        label: formatDate(s.signal_date),
        forecast: s.forecast_qty,
        actual: s.actual_qty ?? 0,
        variance: s.variance_pct ?? 0,
        overThreshold: (s.actual_qty ?? 0) > s.forecast_qty * 1.1,
      }));
  }, [signals]);

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
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-2 rounded" style={{ background: 'rgba(248, 81, 73, 0.3)' }} />
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
            Variance &gt;10%
          </span>
        </div>
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
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={false}
            tickLine={false}
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
              const label = name === 'forecast' ? 'Forecast' : name === 'actual' ? 'Actual' : String(name);
              return [Number(value).toLocaleString(), label];
            }}
            cursor={{ stroke: 'var(--wr-border-active)', strokeWidth: 1, strokeDasharray: '4 4' }}
          />

          {/* Highlight variance > 10% zones */}
          {chartData
            .filter((d) => d.overThreshold)
            .map((d) => (
              <ReferenceLine
                key={d.date}
                x={d.label}
                stroke="var(--wr-red)"
                strokeDasharray="3 3"
                strokeOpacity={0.3}
              />
            ))}

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
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
