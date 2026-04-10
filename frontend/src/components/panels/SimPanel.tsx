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
import { ScenarioBuilder } from './ScenarioBuilder';
import { ScenarioComparison } from './ScenarioComparison';
import { ExecutiveSummaryModal } from './ExecutiveSummaryModal';
import type { CustomScenario } from './ScenarioBuilder';
import type { SimulationBrief } from '../../types/api';

type SimMode = 'presets' | 'custom';
const COMPARE_MIN = 2;
const COMPARE_MAX = 5;

const PRESET_SCENARIOS = [
  { id: 'suez_closure', name: 'Suez Canal Closure', description: '21-day closure of all ocean freight through the Suez Canal' },
  { id: 'china_lockdown', name: 'Shanghai Port Congestion', description: '14-day severe congestion drops Shanghai throughput to 30%' },
  { id: 'demand_spike', name: 'Demand Shock +60%', description: '45-day demand surge strains logistics and depletes safety stock' },
  { id: 'supplier_failure', name: 'Key Supplier Failure', description: '30-day shutdown of highest-volume East Asia supplier' },
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
              style={{
                background: 'var(--wr-bg-primary)',
                border: `1px solid ${worse ? 'rgba(248, 81, 73, 0.2)' : 'rgba(63, 185, 80, 0.2)'}`,
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
                  {m.label}
                </span>
                <span
                  className="text-[10px] font-mono-numbers font-semibold"
                  style={{ color: worse ? 'var(--wr-red)' : 'var(--wr-green)' }}
                >
                  {worse ? '\u25B2' : '\u25BC'}
                </span>
              </div>
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
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2332" strokeOpacity={0.6} vertical={false} />
          <XAxis
            dataKey="metric"
            tick={{ fontSize: 10, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }}
            axisLine={{ stroke: '#1a2332' }}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 10, fill: 'var(--wr-text-muted)', fontFamily: 'var(--wr-font-mono)' }} axisLine={false} tickLine={false} />
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
          />
          <Legend wrapperStyle={{ fontSize: 10, color: 'var(--wr-text-muted)' }} />
          <Bar dataKey="Baseline" fill="#58a6ff" radius={[3, 3, 0, 0]} opacity={0.85} />
          <Bar dataKey="Mitigated" fill="#3fb950" radius={[3, 3, 0, 0]} opacity={0.85} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimPanel({ className }: { className?: string }) {
  const { data: simulations, isLoading, error } = useSimulations();
  const runMutation = useRunSimulation();
  const [mode, setMode] = useState<SimMode>('presets');
  const [selectedScenario, setSelectedScenario] = useState(PRESET_SCENARIOS[0].id);
  const [selectedSimId, setSelectedSimId] = useState<string | null>(null);
  const [showBrief, setShowBrief] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  const { data: selectedSim } = useSimulation(selectedSimId ?? '');

  const toggleCompareId = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < COMPARE_MAX ? [...prev, id] : prev,
    );
  };

  const handleRunSimulation = () => {
    const preset = PRESET_SCENARIOS.find((s) => s.id === selectedScenario);
    if (!preset) return;
    runMutation.mutate({
      name: preset.name,
      scenario_params: { scenario: preset.id },
    });
  };

  const handleRunCustom = (scenario: CustomScenario) => {
    runMutation.mutate({
      name: scenario.name,
      description: scenario.description,
      scenario_params: {
        name: scenario.name,
        description: scenario.description,
        time_horizon_days: scenario.time_horizon_days,
        disruptions: scenario.disruptions.map((d) => ({
          type: d.type,
          affected_ids: [],
          severity: d.severity,
          duration_days: d.duration_days,
          parameters: d.parameters,
        })),
      },
    });
  };

  if (isLoading) return <LoadingSpinner label="Loading simulations..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;

  const baselineMetrics = selectedSim ? parseJsonField(selectedSim.baseline_metrics) : null;
  const mitigatedMetrics = selectedSim ? parseJsonField(selectedSim.mitigated_metrics) : null;

  return (
    <Card className={className} title="Simulation Lab">
      {/* Mode toggle */}
      <div className="flex rounded-md mb-4 overflow-hidden" style={{ border: '1px solid var(--wr-border)' }}>
        {(['presets', 'custom'] as const).map((m) => (
          <button
            key={m}
            className="flex-1 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition-all duration-150"
            style={{
              background: mode === m ? 'rgba(88, 166, 255, 0.15)' : 'transparent',
              color: mode === m ? 'var(--wr-cyan)' : 'var(--wr-text-muted)',
              borderRight: m === 'presets' ? '1px solid var(--wr-border)' : 'none',
            }}
            onClick={() => setMode(m)}
          >
            {m === 'presets' ? 'Presets' : 'Custom Builder'}
          </button>
        ))}
      </div>

      {mode === 'presets' ? (
        <>
          {/* Preset controls */}
          <div className="flex items-end gap-3 mb-4">
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wider block mb-1" style={{ color: 'var(--wr-text-muted)' }}>
                Scenario
              </label>
              <select
                className="w-full px-3 py-2 rounded-md text-sm font-mono-numbers cursor-pointer transition-all duration-150"
                style={{
                  background: 'var(--wr-bg-primary)',
                  border: '1px solid var(--wr-border)',
                  color: 'var(--wr-text-primary)',
                  outline: 'none',
                  appearance: 'none',
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23484f58' d='M2 4l4 4 4-4'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 10px center',
                  paddingRight: '30px',
                }}
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                onFocus={(e) => { (e.target as HTMLElement).style.borderColor = 'var(--wr-cyan)'; }}
                onBlur={(e) => { (e.target as HTMLElement).style.borderColor = 'var(--wr-border)'; }}
              >
                {PRESET_SCENARIOS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="px-5 py-2 rounded-md text-sm font-semibold transition-all duration-200 flex items-center gap-2 flex-shrink-0"
              style={{
                background: runMutation.isPending
                  ? 'var(--wr-border)'
                  : 'linear-gradient(135deg, rgba(88, 166, 255, 0.2), rgba(88, 166, 255, 0.1))',
                color: runMutation.isPending ? 'var(--wr-text-muted)' : 'var(--wr-cyan)',
                border: `1px solid ${runMutation.isPending ? 'var(--wr-border)' : 'rgba(88, 166, 255, 0.4)'}`,
                cursor: runMutation.isPending ? 'not-allowed' : 'pointer',
                boxShadow: runMutation.isPending ? 'none' : '0 0 12px rgba(88, 166, 255, 0.15)',
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
        </>
      ) : (
        <div className="mb-4">
          <ScenarioBuilder onRun={handleRunCustom} isPending={runMutation.isPending} />
        </div>
      )}

      {/* Error from mutation */}
      {runMutation.error && (
        <div className="mb-4 p-2 rounded" style={{ background: 'var(--wr-red-dim)', color: 'var(--wr-red)' }}>
          <span className="text-xs">{(runMutation.error as Error).message}</span>
        </div>
      )}

      {/* Previous simulations list */}
      {simulations && simulations.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
              Previous Runs
            </span>
            {simulations.filter((s: SimulationBrief) => s.status === 'completed').length >= COMPARE_MIN && (
              <button
                className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded transition-all duration-150"
                style={{
                  background: compareMode ? 'rgba(88, 166, 255, 0.15)' : 'transparent',
                  color: compareMode ? 'var(--wr-cyan)' : 'var(--wr-text-muted)',
                  border: `1px solid ${compareMode ? 'rgba(88, 166, 255, 0.3)' : 'var(--wr-border)'}`,
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setCompareMode(!compareMode);
                  setCompareIds([]);
                }}
              >
                {compareMode ? 'Cancel' : 'Compare'}
              </button>
            )}
          </div>
          <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1 mb-4">
            {simulations.map((sim: SimulationBrief) => {
              const isSelected = compareMode ? compareIds.includes(sim.id) : selectedSimId === sim.id;
              const isCompletedSim = sim.status === 'completed';
              return (
                <div
                  key={sim.id}
                  className="flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-all duration-150"
                  style={{
                    background: isSelected ? 'var(--wr-bg-primary)' : 'transparent',
                    border: `1px solid ${isSelected ? 'var(--wr-cyan)' : 'var(--wr-border)'}`,
                    opacity: compareMode && !isCompletedSim ? 0.4 : 1,
                    pointerEvents: compareMode && !isCompletedSim ? 'none' : 'auto',
                  }}
                  onClick={() => {
                    if (compareMode) {
                      toggleCompareId(sim.id);
                    } else {
                      setSelectedSimId(selectedSimId === sim.id ? null : sim.id);
                    }
                  }}
                >
                  {compareMode && (
                    <div
                      className="w-4 h-4 rounded border flex items-center justify-center flex-shrink-0"
                      style={{
                        borderColor: isSelected ? 'var(--wr-cyan)' : 'var(--wr-border)',
                        background: isSelected ? 'rgba(88, 166, 255, 0.2)' : 'transparent',
                      }}
                    >
                      {isSelected && (
                        <span style={{ color: 'var(--wr-cyan)', fontSize: 10, lineHeight: 1 }}>&#10003;</span>
                      )}
                    </div>
                  )}
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
              );
            })}
          </div>

          {/* Compare button */}
          {compareMode && (
            <button
              className="w-full px-4 py-2 rounded-md text-xs font-semibold uppercase tracking-wider transition-all duration-200 mb-4"
              style={{
                background:
                  compareIds.length >= COMPARE_MIN
                    ? 'linear-gradient(135deg, rgba(88, 166, 255, 0.2), rgba(88, 166, 255, 0.1))'
                    : 'var(--wr-bg-primary)',
                color: compareIds.length >= COMPARE_MIN ? 'var(--wr-cyan)' : 'var(--wr-text-muted)',
                border: `1px solid ${compareIds.length >= COMPARE_MIN ? 'rgba(88, 166, 255, 0.4)' : 'var(--wr-border)'}`,
                cursor: compareIds.length >= COMPARE_MIN ? 'pointer' : 'not-allowed',
                boxShadow: compareIds.length >= COMPARE_MIN ? '0 0 12px rgba(88, 166, 255, 0.15)' : 'none',
              }}
              disabled={compareIds.length < COMPARE_MIN}
              onClick={() => setShowComparison(true)}
            >
              Compare {compareIds.length} Scenario{compareIds.length !== 1 ? 's' : ''}
              {compareIds.length < COMPARE_MIN && ` (select ${COMPARE_MIN - compareIds.length} more)`}
            </button>
          )}
        </div>
      )}

      {/* Results comparison */}
      {baselineMetrics && mitigatedMetrics && (
        <div className="animate-fade-in">
          <span className="text-[10px] uppercase tracking-wider block mb-2" style={{ color: 'var(--wr-text-muted)' }}>
            Results: {selectedSim?.name}
          </span>
          <ResultsComparison baseline={baselineMetrics} mitigated={mitigatedMetrics} />
          <button
            className="w-full mt-3 px-4 py-2 rounded-md text-xs font-semibold uppercase tracking-wider transition-all duration-200"
            style={{
              background: 'linear-gradient(135deg, rgba(188, 140, 255, 0.15), rgba(188, 140, 255, 0.05))',
              color: 'var(--wr-purple)',
              border: '1px solid rgba(188, 140, 255, 0.3)',
              cursor: 'pointer',
            }}
            onClick={() => setShowBrief(true)}
          >
            Generate Executive Brief
          </button>
        </div>
      )}

      {showBrief && selectedSimId && (
        <ExecutiveSummaryModal
          simulationId={selectedSimId}
          onClose={() => setShowBrief(false)}
        />
      )}

      {showComparison && compareIds.length >= COMPARE_MIN && (
        <ScenarioComparison
          simulationIds={compareIds}
          onClose={() => setShowComparison(false)}
        />
      )}
    </Card>
  );
}
