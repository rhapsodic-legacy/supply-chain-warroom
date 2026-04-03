import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { useSimulations, useRunSimulation, useSimulation } from '../../hooks/useSimulations';
import type { SimulationBrief } from '../../types/api';

const PRESET_SCENARIOS = [
  { id: 'suez_closure', name: 'Suez Canal Closure', description: 'Simulate full blockage of the Suez Canal' },
  { id: 'china_lockdown', name: 'China Port Lockdown', description: 'Major Chinese port shutdown' },
  { id: 'demand_spike', name: 'Demand Spike +40%', description: 'Sudden 40% increase in demand' },
  { id: 'supplier_failure', name: 'Key Supplier Failure', description: 'Top-tier supplier goes offline' },
  { id: 'energy_crisis', name: 'Energy Price Surge', description: 'Global energy price spike' },
];

interface ParsedMetrics {
  total_cost?: number;
  fill_rate?: number;
  avg_lead_time?: number;
  risk_score?: number;
  [key: string]: unknown;
}

function parseJsonField(raw: string | null): ParsedMetrics | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ParsedMetrics;
  } catch {
    return null;
  }
}

function formatMetric(value: number | undefined, suffix = ''): string {
  if (value === undefined || value === null) return '--';
  if (suffix === '%') return `${(value * 100).toFixed(1)}%`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `${value.toFixed(1)}${suffix}`;
}

function ResultsComparison({ baseline, mitigated }: { baseline: ParsedMetrics; mitigated: ParsedMetrics }) {
  const metrics = [
    { key: 'total_cost', label: 'Total Cost', format: '' },
    { key: 'fill_rate', label: 'Fill Rate', format: '%' },
    { key: 'avg_lead_time', label: 'Avg Lead Time', format: 'd' },
    { key: 'risk_score', label: 'Risk Score', format: '' },
  ] as const;

  const chartData = metrics.map((m) => ({
    metric: m.label,
    Baseline: m.format === '%' ? ((baseline[m.key] as number) ?? 0) * 100 : ((baseline[m.key] as number) ?? 0),
    Mitigated: m.format === '%' ? ((mitigated[m.key] as number) ?? 0) * 100 : ((mitigated[m.key] as number) ?? 0),
  }));

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        {metrics.map((m) => {
          const bVal = baseline[m.key] as number | undefined;
          const mVal = mitigated[m.key] as number | undefined;
          const worse = m.key === 'fill_rate' ? (mVal ?? 0) < (bVal ?? 0) : (mVal ?? 0) > (bVal ?? 0);

          return (
            <div
              key={m.key}
              className="rounded-lg p-3"
              style={{ background: 'var(--wr-bg-primary)', border: '1px solid var(--wr-border)' }}
            >
              <span className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--wr-text-muted)' }}>
                {m.label}
              </span>
              <div className="flex items-end gap-3">
                <div>
                  <span className="text-[10px] block" style={{ color: 'var(--wr-text-muted)' }}>Base</span>
                  <span className="font-mono-numbers text-sm font-bold" style={{ color: 'var(--wr-cyan)' }}>
                    {formatMetric(bVal, m.format)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] block" style={{ color: 'var(--wr-text-muted)' }}>Mitigated</span>
                  <span
                    className="font-mono-numbers text-sm font-bold"
                    style={{ color: worse ? 'var(--wr-red)' : 'var(--wr-green)' }}
                  >
                    {formatMetric(mVal, m.format)}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--wr-border)" vertical={false} />
          <XAxis
            dataKey="metric"
            tick={{ fontSize: 10, fill: '#484f58' }}
            axisLine={{ stroke: 'var(--wr-border)' }}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 10, fill: '#484f58' }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              background: 'var(--wr-bg-elevated)',
              border: '1px solid var(--wr-border-active)',
              borderRadius: 'var(--wr-radius)',
              fontSize: 12,
              color: 'var(--wr-text-primary)',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 10, color: 'var(--wr-text-muted)' }} />
          <Bar dataKey="Baseline" fill="#58a6ff" radius={[3, 3, 0, 0]} />
          <Bar dataKey="Mitigated" fill="#f85149" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimPanel({ className }: { className?: string }) {
  const { data: simulations, isLoading, error } = useSimulations();
  const runMutation = useRunSimulation();
  const [selectedScenario, setSelectedScenario] = useState(PRESET_SCENARIOS[0].id);
  const [selectedSimId, setSelectedSimId] = useState<string | null>(null);

  const { data: selectedSim } = useSimulation(selectedSimId ?? '');

  const handleRunSimulation = () => {
    const preset = PRESET_SCENARIOS.find((s) => s.id === selectedScenario);
    if (!preset) return;
    runMutation.mutate({
      name: preset.name,
      scenario_params: { scenario: preset.id },
    });
  };

  if (isLoading) return <LoadingSpinner label="Loading simulations..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;

  const baselineMetrics = selectedSim ? parseJsonField(selectedSim.baseline_metrics) : null;
  const mitigatedMetrics = selectedSim ? parseJsonField(selectedSim.mitigated_metrics) : null;

  return (
    <Card className={className} title="Simulation Lab">
      {/* Controls */}
      <div className="flex items-end gap-3 mb-4">
        <div className="flex-1">
          <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--wr-text-muted)' }}>
            Scenario
          </label>
          <select
            className="w-full px-3 py-2 rounded-md text-sm"
            style={{
              background: 'var(--wr-bg-primary)',
              border: '1px solid var(--wr-border)',
              color: 'var(--wr-text-primary)',
              outline: 'none',
            }}
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
          >
            {PRESET_SCENARIOS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <button
          className="px-4 py-2 rounded-md text-sm font-semibold transition-all duration-200 flex items-center gap-2"
          style={{
            background: runMutation.isPending ? 'var(--wr-border)' : 'var(--wr-cyan-dim)',
            color: runMutation.isPending ? 'var(--wr-text-muted)' : 'var(--wr-cyan)',
            border: `1px solid ${runMutation.isPending ? 'var(--wr-border)' : 'rgba(88, 166, 255, 0.3)'}`,
            cursor: runMutation.isPending ? 'not-allowed' : 'pointer',
          }}
          onClick={handleRunSimulation}
          disabled={runMutation.isPending}
        >
          {runMutation.isPending && <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />}
          {runMutation.isPending ? 'Running...' : 'Run Simulation'}
        </button>
      </div>

      {/* Scenario description */}
      <p className="text-xs mb-4" style={{ color: 'var(--wr-text-secondary)' }}>
        {PRESET_SCENARIOS.find((s) => s.id === selectedScenario)?.description}
      </p>

      {/* Error from mutation */}
      {runMutation.error && (
        <div className="mb-4 p-2 rounded" style={{ background: 'var(--wr-red-dim)', color: 'var(--wr-red)' }}>
          <span className="text-xs">{(runMutation.error as Error).message}</span>
        </div>
      )}

      {/* Previous simulations list */}
      {simulations && simulations.length > 0 && (
        <div>
          <span className="text-[10px] uppercase tracking-wider block mb-2" style={{ color: 'var(--wr-text-muted)' }}>
            Previous Runs
          </span>
          <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1 mb-4">
            {simulations.map((sim: SimulationBrief) => (
              <div
                key={sim.id}
                className="flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-all duration-150"
                style={{
                  background: selectedSimId === sim.id ? 'var(--wr-bg-primary)' : 'transparent',
                  border: `1px solid ${selectedSimId === sim.id ? 'var(--wr-cyan)' : 'var(--wr-border)'}`,
                }}
                onClick={() => setSelectedSimId(selectedSimId === sim.id ? null : sim.id)}
              >
                <Badge
                  severity={
                    sim.status === 'completed'
                      ? 'low'
                      : sim.status === 'running'
                        ? 'info'
                        : sim.status === 'failed'
                          ? 'critical'
                          : 'medium'
                  }
                >
                  {sim.status}
                </Badge>
                <span className="text-xs truncate flex-1" style={{ color: 'var(--wr-text-primary)' }}>
                  {sim.name}
                </span>
                <span className="font-mono-numbers text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                  {new Date(sim.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results comparison */}
      {baselineMetrics && mitigatedMetrics && (
        <div className="animate-fade-in">
          <span className="text-[10px] uppercase tracking-wider block mb-2" style={{ color: 'var(--wr-text-muted)' }}>
            Results: {selectedSim?.name}
          </span>
          <ResultsComparison baseline={baselineMetrics} mitigated={mitigatedMetrics} />
        </div>
      )}
    </Card>
  );
}
