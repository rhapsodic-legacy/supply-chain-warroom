import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { useCompareSimulations } from '../../hooks/useSimulations';
import type { SimulationCompareItem, HistogramData } from '../../types/api';

const SCENARIO_COLORS = ['#58a6ff', '#f0883e', '#3fb950', '#bc8cff', '#f85149'];

interface ParsedMetrics {
  total_cost?: number;
  fill_rate?: number;
  avg_lead_time?: number;
  risk_score?: number;
}

interface ParsedComparison {
  cost_change_pct?: number;
  fill_rate_change?: number;
  delay_change_days?: number;
  cost_p95?: number;
  delay_p95?: number;
  stockout_mean?: number;
  histograms?: {
    cost?: HistogramData;
    delay?: HistogramData;
  };
}

function parseJson<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function formatCost(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

interface ScenarioParsed {
  id: string;
  name: string;
  baseline: ParsedMetrics;
  mitigated: ParsedMetrics;
  comparison: ParsedComparison;
  color: string;
}

function buildDistributionChartData(
  scenarios: ScenarioParsed[],
  metric: 'cost' | 'delay',
): { data: { bin: string; [key: string]: string | number }[]; hasData: boolean } {
  const histograms: { name: string; histogram: HistogramData; color: string }[] = [];
  for (const s of scenarios) {
    const h = s.comparison.histograms?.[metric];
    if (h && h.bin_edges.length > 0) {
      histograms.push({ name: s.name, histogram: h, color: s.color });
    }
  }
  if (histograms.length === 0) return { data: [], hasData: false };

  // Normalize counts to density (fraction of total) for fair comparison
  const allBins = new Set<number>();
  for (const h of histograms) {
    for (let i = 0; i < h.histogram.bin_edges.length - 1; i++) {
      const mid = (h.histogram.bin_edges[i] + h.histogram.bin_edges[i + 1]) / 2;
      allBins.add(Math.round(mid * 100) / 100);
    }
  }
  const sortedBins = Array.from(allBins).sort((a, b) => a - b);

  const data = sortedBins.map((bin) => {
    const row: { bin: string; [key: string]: string | number } = {
      bin: metric === 'cost' ? formatCost(bin) : `${bin.toFixed(1)}d`,
    };
    for (const h of histograms) {
      const totalCount = h.histogram.counts.reduce((a, b) => a + b, 0);
      // Find the bin this value falls into
      let density = 0;
      for (let i = 0; i < h.histogram.bin_edges.length - 1; i++) {
        const mid = (h.histogram.bin_edges[i] + h.histogram.bin_edges[i + 1]) / 2;
        if (Math.abs(mid - bin) < 0.01 * Math.max(Math.abs(bin), 1)) {
          density = totalCount > 0 ? (h.histogram.counts[i] / totalCount) * 100 : 0;
          break;
        }
      }
      row[h.name] = Math.round(density * 10) / 10;
    }
    return row;
  });

  return { data, hasData: true };
}

function DistributionChart({
  scenarios,
  metric,
  title,
}: {
  scenarios: ScenarioParsed[];
  metric: 'cost' | 'delay';
  title: string;
}) {
  const { data, hasData } = buildDistributionChartData(scenarios, metric);
  if (!hasData) return null;

  // Downsample if too many bins for readability
  const displayData = data.length > 20 ? data.filter((_, i) => i % Math.ceil(data.length / 20) === 0) : data;

  return (
    <div>
      <span
        className="text-[10px] uppercase tracking-wider block mb-2"
        style={{ color: 'var(--wr-text-muted)' }}
      >
        {title}
      </span>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={displayData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2332" strokeOpacity={0.6} vertical={false} />
          <XAxis
            dataKey="bin"
            tick={{ fontSize: 9, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={{ stroke: '#1a2332' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={false}
            tickLine={false}
            label={{
              value: '% of runs',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 9, fill: 'var(--wr-text-muted)' },
            }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--wr-bg-elevated)',
              border: '1px solid var(--wr-border-active)',
              borderRadius: 'var(--wr-radius)',
              fontSize: 11,
              color: 'var(--wr-text-primary)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
              fontFamily: 'var(--wr-font-mono)',
            }}
            formatter={(value) => value != null ? [`${value}%`, undefined] : ['', undefined]}
          />
          <Legend wrapperStyle={{ fontSize: 10, color: 'var(--wr-text-muted)' }} />
          {scenarios.map((s) => (
            <Area
              key={s.id}
              type="monotone"
              dataKey={s.name}
              stroke={s.color}
              fill={s.color}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function MetricsRankingTable({ scenarios }: { scenarios: ScenarioParsed[] }) {
  const metrics = [
    {
      key: 'cost_change_pct',
      label: 'Cost Impact',
      getValue: (s: ScenarioParsed) => s.comparison.cost_change_pct ?? 0,
      format: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
      lowerIsBetter: true,
    },
    {
      key: 'fill_rate',
      label: 'Fill Rate (Mitigated)',
      getValue: (s: ScenarioParsed) => s.mitigated.fill_rate ?? 0,
      format: (v: number) => formatPct(v),
      lowerIsBetter: false,
    },
    {
      key: 'delay_change',
      label: 'Delay Change',
      getValue: (s: ScenarioParsed) => s.comparison.delay_change_days ?? 0,
      format: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}d`,
      lowerIsBetter: true,
    },
    {
      key: 'cost_p95',
      label: 'Cost P95',
      getValue: (s: ScenarioParsed) => s.comparison.cost_p95 ?? 0,
      format: (v: number) => formatCost(v),
      lowerIsBetter: true,
    },
    {
      key: 'stockout',
      label: 'Avg Stockout Days',
      getValue: (s: ScenarioParsed) => s.comparison.stockout_mean ?? 0,
      format: (v: number) => `${v.toFixed(1)}d`,
      lowerIsBetter: true,
    },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
        <thead>
          <tr>
            <th
              className="text-left py-2 px-2 text-[10px] uppercase tracking-wider"
              style={{ color: 'var(--wr-text-muted)', borderBottom: '1px solid var(--wr-border)' }}
            >
              Metric
            </th>
            {scenarios.map((s) => (
              <th
                key={s.id}
                className="text-right py-2 px-2 text-[10px] uppercase tracking-wider"
                style={{
                  color: s.color,
                  borderBottom: '1px solid var(--wr-border)',
                }}
              >
                {s.name.length > 16 ? s.name.slice(0, 14) + '...' : s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => {
            const values = scenarios.map((s) => m.getValue(s));
            const best = m.lowerIsBetter ? Math.min(...values) : Math.max(...values);

            return (
              <tr key={m.key}>
                <td
                  className="py-1.5 px-2"
                  style={{ color: 'var(--wr-text-secondary)', borderBottom: '1px solid var(--wr-border)' }}
                >
                  {m.label}
                </td>
                {scenarios.map((s, i) => {
                  const val = values[i];
                  const isBest = val === best;
                  return (
                    <td
                      key={s.id}
                      className="text-right py-1.5 px-2 font-mono-numbers"
                      style={{
                        color: isBest ? 'var(--wr-green)' : 'var(--wr-text-primary)',
                        fontWeight: isBest ? 600 : 400,
                        borderBottom: '1px solid var(--wr-border)',
                      }}
                    >
                      {m.format(val)}
                      {isBest && <span className="ml-1 text-[9px]">*</span>}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RadarComparisonChart({ scenarios }: { scenarios: ScenarioParsed[] }) {
  // Normalize metrics to 0-100 scale for radar chart
  const dimensions = [
    { key: 'cost_impact', label: 'Cost Impact', getValue: (s: ScenarioParsed) => Math.abs(s.comparison.cost_change_pct ?? 0) },
    { key: 'fill_rate', label: 'Fill Rate', getValue: (s: ScenarioParsed) => (s.mitigated.fill_rate ?? 0) * 100 },
    { key: 'delay', label: 'Delay', getValue: (s: ScenarioParsed) => Math.abs(s.comparison.delay_change_days ?? 0) },
    { key: 'stockout', label: 'Stockout', getValue: (s: ScenarioParsed) => s.comparison.stockout_mean ?? 0 },
    { key: 'risk', label: 'Risk Score', getValue: (s: ScenarioParsed) => (s.mitigated.risk_score ?? 0) * 100 },
  ];

  // Normalize each dimension to 0-100 across all scenarios
  const maxes = dimensions.map((d) => Math.max(...scenarios.map((s) => d.getValue(s)), 1));

  const data = dimensions.map((d, di) => {
    const row: { dimension: string; [key: string]: string | number } = { dimension: d.label };
    for (const s of scenarios) {
      row[s.name] = Math.round((d.getValue(s) / maxes[di]) * 100);
    }
    return row;
  });

  return (
    <div>
      <span
        className="text-[10px] uppercase tracking-wider block mb-2"
        style={{ color: 'var(--wr-text-muted)' }}
      >
        Risk Profile Overlay
      </span>
      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#1a2332" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 9, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
          />
          <PolarRadiusAxis tick={false} axisLine={false} />
          {scenarios.map((s) => (
            <Radar
              key={s.id}
              name={s.name}
              dataKey={s.name}
              stroke={s.color}
              fill={s.color}
              fillOpacity={0.1}
              strokeWidth={2}
            />
          ))}
          <Legend wrapperStyle={{ fontSize: 10, color: 'var(--wr-text-muted)' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ScenarioComparison({
  simulationIds,
  onClose,
}: {
  simulationIds: string[];
  onClose: () => void;
}) {
  const { data, isLoading, error } = useCompareSimulations(simulationIds);

  if (isLoading) return <LoadingSpinner label="Comparing scenarios..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!data) return null;

  const scenarios: ScenarioParsed[] = data.simulations
    .map((sim: SimulationCompareItem, i: number) => {
      const baseline = parseJson<ParsedMetrics>(sim.baseline_metrics);
      const mitigated = parseJson<ParsedMetrics>(sim.mitigated_metrics);
      const comparison = parseJson<ParsedComparison>(sim.comparison);
      if (!baseline || !mitigated || !comparison) return null;
      return {
        id: sim.id,
        name: sim.name,
        baseline,
        mitigated,
        comparison,
        color: SCENARIO_COLORS[i % SCENARIO_COLORS.length],
      };
    })
    .filter(Boolean) as ScenarioParsed[];

  if (scenarios.length < 2) {
    return <ErrorCard message="Not enough valid simulation results to compare" />;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-lg p-5"
        style={{
          background: 'var(--wr-bg-secondary)',
          border: '1px solid var(--wr-border-active)',
          boxShadow: '0 0 40px rgba(88, 166, 255, 0.1)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--wr-text-primary)' }}>
              Scenario Comparison
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--wr-text-muted)' }}>
              {scenarios.length} scenarios compared side-by-side
            </p>
          </div>
          <button
            className="px-3 py-1.5 rounded text-xs"
            style={{
              background: 'var(--wr-bg-primary)',
              color: 'var(--wr-text-muted)',
              border: '1px solid var(--wr-border)',
              cursor: 'pointer',
            }}
            onClick={onClose}
          >
            Close
          </button>
        </div>

        {/* Scenario legend */}
        <div className="flex flex-wrap gap-3 mb-5">
          {scenarios.map((s) => (
            <div key={s.id} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ background: s.color }} />
              <span className="text-xs" style={{ color: 'var(--wr-text-primary)' }}>
                {s.name}
              </span>
            </div>
          ))}
        </div>

        {/* Metrics ranking table */}
        <div
          className="rounded-lg p-3 mb-5"
          style={{ background: 'var(--wr-bg-primary)', border: '1px solid var(--wr-border)' }}
        >
          <span
            className="text-[10px] uppercase tracking-wider block mb-2"
            style={{ color: 'var(--wr-text-muted)' }}
          >
            Metrics Comparison (* = best)
          </span>
          <MetricsRankingTable scenarios={scenarios} />
        </div>

        {/* Radar chart */}
        <div
          className="rounded-lg p-3 mb-5"
          style={{ background: 'var(--wr-bg-primary)', border: '1px solid var(--wr-border)' }}
        >
          <RadarComparisonChart scenarios={scenarios} />
        </div>

        {/* Distribution overlays */}
        <div className="grid grid-cols-1 gap-4">
          <div
            className="rounded-lg p-3"
            style={{ background: 'var(--wr-bg-primary)', border: '1px solid var(--wr-border)' }}
          >
            <DistributionChart scenarios={scenarios} metric="cost" title="Cost Distribution Overlay" />
          </div>
          <div
            className="rounded-lg p-3"
            style={{ background: 'var(--wr-bg-primary)', border: '1px solid var(--wr-border)' }}
          >
            <DistributionChart scenarios={scenarios} metric="delay" title="Delay Distribution Overlay" />
          </div>
        </div>
      </div>
    </div>
  );
}
