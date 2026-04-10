import { useState } from 'react';

/* ─── Disruption type metadata ─── */
const DISRUPTION_TYPES = [
  {
    value: 'route_closure',
    label: 'Route Closure',
    description: 'Completely blocks shipping routes',
    icon: '\u26D4',
    defaultParams: { match_transport: 'ocean' },
  },
  {
    value: 'capacity_reduction',
    label: 'Capacity Reduction',
    description: 'Reduces throughput at a port or route',
    icon: '\u26A0',
    defaultParams: { remaining_fraction: 0.3, match_port: '' },
  },
  {
    value: 'node_shutdown',
    label: 'Supplier Shutdown',
    description: 'Complete shutdown of a supplier node',
    icon: '\u2B24',
    defaultParams: { match_region: 'East Asia', pick: 'highest_capacity' },
  },
  {
    value: 'demand_spike',
    label: 'Demand Spike',
    description: 'Sudden surge in product demand',
    icon: '\u2191',
    defaultParams: { demand_multiplier: 1.6, category: 'electronics' },
  },
  {
    value: 'cost_increase',
    label: 'Cost Increase',
    description: 'Raises transport or material costs',
    icon: '\u0024',
    defaultParams: { cost_multiplier: 1.5 },
  },
] as const;

const TRANSPORT_MODES = ['ocean', 'air', 'rail', 'truck'];
const REGIONS = ['East Asia', 'Southeast Asia', 'South Asia', 'Europe', 'North America'];

export interface CustomScenario {
  name: string;
  description: string;
  time_horizon_days: number;
  disruptions: DisruptionDraft[];
}

interface DisruptionDraft {
  type: string;
  severity: number;
  duration_days: number;
  parameters: Record<string, unknown>;
}

function newDisruption(): DisruptionDraft {
  return {
    type: 'route_closure',
    severity: 0.7,
    duration_days: 14,
    parameters: { ...DISRUPTION_TYPES[0].defaultParams },
  };
}

/* ─── Shared input styling ─── */
const inputStyle: React.CSSProperties = {
  background: 'var(--wr-bg-primary)',
  border: '1px solid var(--wr-border)',
  color: 'var(--wr-text-primary)',
  outline: 'none',
};

const labelClasses = 'text-[10px] uppercase tracking-wider block mb-1';

/* ─── Parameter editors per disruption type ─── */
function DisruptionParams({
  type,
  parameters,
  onChange,
}: {
  type: string;
  parameters: Record<string, unknown>;
  onChange: (params: Record<string, unknown>) => void;
}) {
  const set = (key: string, value: unknown) => onChange({ ...parameters, [key]: value });

  switch (type) {
    case 'route_closure':
      return (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Transport Mode
            </span>
            <select
              className="w-full px-2 py-1.5 rounded text-xs"
              style={inputStyle}
              value={(parameters.match_transport as string) ?? 'ocean'}
              onChange={(e) => set('match_transport', e.target.value)}
            >
              {TRANSPORT_MODES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
      );

    case 'capacity_reduction':
      return (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Remaining Capacity
            </span>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={5}
                max={90}
                step={5}
                className="flex-1 accent-cyan-400"
                value={((parameters.remaining_fraction as number) ?? 0.3) * 100}
                onChange={(e) => set('remaining_fraction', Number(e.target.value) / 100)}
              />
              <span className="font-mono-numbers text-xs w-10 text-right" style={{ color: 'var(--wr-cyan)' }}>
                {Math.round(((parameters.remaining_fraction as number) ?? 0.3) * 100)}%
              </span>
            </div>
          </div>
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Port Name
            </span>
            <input
              type="text"
              className="w-full px-2 py-1.5 rounded text-xs"
              style={inputStyle}
              placeholder="e.g. Shanghai"
              value={(parameters.match_port as string) ?? ''}
              onChange={(e) => set('match_port', e.target.value)}
            />
          </div>
        </div>
      );

    case 'node_shutdown':
      return (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Region
            </span>
            <select
              className="w-full px-2 py-1.5 rounded text-xs"
              style={inputStyle}
              value={(parameters.match_region as string) ?? 'East Asia'}
              onChange={(e) => set('match_region', e.target.value)}
            >
              {REGIONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Target Selection
            </span>
            <select
              className="w-full px-2 py-1.5 rounded text-xs"
              style={inputStyle}
              value={(parameters.pick as string) ?? 'highest_capacity'}
              onChange={(e) => set('pick', e.target.value)}
            >
              <option value="highest_capacity">Highest Capacity</option>
              <option value="random">Random</option>
            </select>
          </div>
        </div>
      );

    case 'demand_spike':
      return (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Demand Multiplier
            </span>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={110}
                max={300}
                step={10}
                className="flex-1 accent-cyan-400"
                value={((parameters.demand_multiplier as number) ?? 1.6) * 100}
                onChange={(e) => set('demand_multiplier', Number(e.target.value) / 100)}
              />
              <span className="font-mono-numbers text-xs w-12 text-right" style={{ color: 'var(--wr-cyan)' }}>
                {Math.round(((parameters.demand_multiplier as number) ?? 1.6) * 100)}%
              </span>
            </div>
          </div>
          <div>
            <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
              Category
            </span>
            <input
              type="text"
              className="w-full px-2 py-1.5 rounded text-xs"
              style={inputStyle}
              placeholder="e.g. electronics"
              value={(parameters.category as string) ?? ''}
              onChange={(e) => set('category', e.target.value)}
            />
          </div>
        </div>
      );

    case 'cost_increase':
      return (
        <div>
          <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
            Cost Multiplier
          </span>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={110}
              max={400}
              step={10}
              className="flex-1 accent-cyan-400"
              value={((parameters.cost_multiplier as number) ?? 1.5) * 100}
              onChange={(e) => set('cost_multiplier', Number(e.target.value) / 100)}
            />
            <span className="font-mono-numbers text-xs w-12 text-right" style={{ color: 'var(--wr-cyan)' }}>
              {Math.round(((parameters.cost_multiplier as number) ?? 1.5) * 100)}%
            </span>
          </div>
        </div>
      );

    default:
      return null;
  }
}

/* ─── Single disruption card ─── */
function DisruptionCard({
  disruption,
  index,
  onChange,
  onRemove,
  canRemove,
}: {
  disruption: DisruptionDraft;
  index: number;
  onChange: (d: DisruptionDraft) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const meta = DISRUPTION_TYPES.find((t) => t.value === disruption.type);

  const handleTypeChange = (newType: string) => {
    const newMeta = DISRUPTION_TYPES.find((t) => t.value === newType);
    onChange({
      ...disruption,
      type: newType,
      parameters: { ...(newMeta?.defaultParams ?? {}) },
    });
  };

  return (
    <div
      className="rounded-lg p-3 space-y-3"
      style={{
        background: 'var(--wr-bg-primary)',
        border: '1px solid var(--wr-border)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold" style={{ color: 'var(--wr-text-secondary)' }}>
          {meta?.icon} Disruption {index + 1}
        </span>
        {canRemove && (
          <button
            className="text-[10px] px-2 py-0.5 rounded transition-colors"
            style={{ color: 'var(--wr-red)', border: '1px solid rgba(248, 81, 73, 0.3)' }}
            onClick={onRemove}
          >
            Remove
          </button>
        )}
      </div>

      {/* Type selector */}
      <div>
        <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>Type</span>
        <select
          className="w-full px-2 py-1.5 rounded text-xs"
          style={inputStyle}
          value={disruption.type}
          onChange={(e) => handleTypeChange(e.target.value)}
        >
          {DISRUPTION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.icon} {t.label} — {t.description}
            </option>
          ))}
        </select>
      </div>

      {/* Severity + Duration row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>Severity</span>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={10}
              max={100}
              step={5}
              className="flex-1 accent-red-400"
              value={disruption.severity * 100}
              onChange={(e) =>
                onChange({ ...disruption, severity: Number(e.target.value) / 100 })
              }
            />
            <span
              className="font-mono-numbers text-xs w-10 text-right font-semibold"
              style={{
                color:
                  disruption.severity >= 0.8
                    ? 'var(--wr-red)'
                    : disruption.severity >= 0.5
                      ? 'var(--wr-amber)'
                      : 'var(--wr-green)',
              }}
            >
              {Math.round(disruption.severity * 100)}%
            </span>
          </div>
        </div>
        <div>
          <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
            Duration (days)
          </span>
          <input
            type="number"
            min={1}
            max={180}
            className="w-full px-2 py-1.5 rounded text-xs font-mono-numbers"
            style={inputStyle}
            value={disruption.duration_days}
            onChange={(e) =>
              onChange({ ...disruption, duration_days: Math.max(1, Number(e.target.value)) })
            }
          />
        </div>
      </div>

      {/* Type-specific parameters */}
      <DisruptionParams
        type={disruption.type}
        parameters={disruption.parameters}
        onChange={(params) => onChange({ ...disruption, parameters: params })}
      />
    </div>
  );
}

/* ─── Main ScenarioBuilder ─── */
export function ScenarioBuilder({
  onRun,
  isPending,
}: {
  onRun: (scenario: CustomScenario) => void;
  isPending: boolean;
}) {
  const [name, setName] = useState('Custom Scenario');
  const [description, setDescription] = useState('');
  const [timeHorizon, setTimeHorizon] = useState(90);
  const [disruptions, setDisruptions] = useState<DisruptionDraft[]>([newDisruption()]);

  const updateDisruption = (index: number, d: DisruptionDraft) => {
    setDisruptions((prev) => prev.map((item, i) => (i === index ? d : item)));
  };

  const removeDisruption = (index: number) => {
    setDisruptions((prev) => prev.filter((_, i) => i !== index));
  };

  const addDisruption = () => {
    setDisruptions((prev) => [...prev, newDisruption()]);
  };

  const handleRun = () => {
    onRun({ name, description, time_horizon_days: timeHorizon, disruptions });
  };

  return (
    <div className="space-y-3">
      {/* Scenario name + time horizon */}
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
            Scenario Name
          </span>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-md text-sm"
            style={inputStyle}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My custom scenario"
          />
        </div>
        <div>
          <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
            Horizon (days)
          </span>
          <input
            type="number"
            min={7}
            max={365}
            className="w-full px-3 py-2 rounded-md text-sm font-mono-numbers"
            style={inputStyle}
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(Math.max(7, Number(e.target.value)))}
          />
        </div>
      </div>

      {/* Description */}
      <div>
        <span className={labelClasses} style={{ color: 'var(--wr-text-muted)' }}>
          Description
        </span>
        <textarea
          className="w-full px-3 py-2 rounded-md text-xs resize-none"
          style={{ ...inputStyle, minHeight: 48 }}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the disruption scenario..."
          rows={2}
        />
      </div>

      {/* Disruptions list */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
            Disruptions ({disruptions.length})
          </span>
          <button
            className="text-[10px] px-2 py-0.5 rounded transition-colors"
            style={{
              color: 'var(--wr-cyan)',
              border: '1px solid rgba(88, 166, 255, 0.3)',
            }}
            onClick={addDisruption}
          >
            + Add Disruption
          </button>
        </div>

        <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
          {disruptions.map((d, i) => (
            <DisruptionCard
              key={i}
              disruption={d}
              index={i}
              onChange={(updated) => updateDisruption(i, updated)}
              onRemove={() => removeDisruption(i)}
              canRemove={disruptions.length > 1}
            />
          ))}
        </div>
      </div>

      {/* Run button */}
      <button
        className="w-full px-5 py-2.5 rounded-md text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2"
        style={{
          background: isPending
            ? 'var(--wr-border)'
            : 'linear-gradient(135deg, rgba(88, 166, 255, 0.2), rgba(88, 166, 255, 0.1))',
          color: isPending ? 'var(--wr-text-muted)' : 'var(--wr-cyan)',
          border: `1px solid ${isPending ? 'var(--wr-border)' : 'rgba(88, 166, 255, 0.4)'}`,
          cursor: isPending ? 'not-allowed' : 'pointer',
          boxShadow: isPending ? 'none' : '0 0 12px rgba(88, 166, 255, 0.15)',
        }}
        onClick={handleRun}
        disabled={isPending || !name.trim() || disruptions.length === 0}
      >
        {isPending && <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />}
        {isPending ? 'Running Simulation...' : 'Run Custom Simulation'}
      </button>
    </div>
  );
}
