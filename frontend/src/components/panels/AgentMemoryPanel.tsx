import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useMemories, useMemoryDetail, useMemoryStats } from '../../hooks/useMemories';

const OUTCOME_CONFIG: Record<string, { color: string; label: string }> = {
  effective: { color: 'var(--wr-green)', label: 'EFFECTIVE' },
  partially_effective: { color: 'var(--wr-amber)', label: 'PARTIAL' },
  ineffective: { color: 'var(--wr-red)', label: 'INEFFECTIVE' },
  pending: { color: 'var(--wr-cyan)', label: 'PENDING' },
};

const CATEGORY_LABELS: Record<string, string> = {
  port_closure: 'Port Closure',
  supplier_failure: 'Supplier Failure',
  weather_disruption: 'Weather',
  demand_spike: 'Demand Spike',
  geopolitical: 'Geopolitical',
  logistics_bottleneck: 'Logistics',
};

const AGENT_COLORS: Record<string, string> = {
  risk_monitor: '#f85149',
  strategy: '#bc8cff',
  execution: '#58a6ff',
  simulation: '#3fb950',
  orchestrator: '#d2a8ff',
};

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

function DetailField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2.5">
      <span
        className="text-[10px] uppercase tracking-wider block mb-0.5"
        style={{ color: 'var(--wr-text-muted)' }}
      >
        {label}
      </span>
      <div className="text-xs leading-relaxed" style={{ color: 'var(--wr-text-secondary)' }}>
        {children}
      </div>
    </div>
  );
}

function StatsBar() {
  const { data: stats } = useMemoryStats();
  if (!stats || stats.total_memories === 0) return null;

  const effective = stats.by_outcome['effective'] ?? 0;
  const partial = stats.by_outcome['partially_effective'] ?? 0;
  const ineffective = stats.by_outcome['ineffective'] ?? 0;
  const total = effective + partial + ineffective || 1;

  return (
    <div className="mb-3 px-1">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
          Learning Effectiveness
        </span>
        <span className="text-[10px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
          {stats.total_memories} memories
        </span>
      </div>
      <div className="flex h-1.5 rounded-full overflow-hidden gap-px">
        {effective > 0 && (
          <div
            style={{ width: `${(effective / total) * 100}%`, background: 'var(--wr-green)' }}
            title={`${effective} effective`}
          />
        )}
        {partial > 0 && (
          <div
            style={{ width: `${(partial / total) * 100}%`, background: 'var(--wr-amber)' }}
            title={`${partial} partially effective`}
          />
        )}
        {ineffective > 0 && (
          <div
            style={{ width: `${(ineffective / total) * 100}%`, background: 'var(--wr-red)' }}
            title={`${ineffective} ineffective`}
          />
        )}
      </div>
    </div>
  );
}

export function AgentMemoryPanel({ className }: { className?: string }) {
  const { data: memories, isLoading, error } = useMemories();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { data: detail } = useMemoryDetail(expandedId);

  if (isLoading) return <LoadingSpinner label="Loading agent memory..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!memories?.length) return <EmptyState message="No learned patterns yet" />;

  const sorted = [...memories].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <Card
      className={className}
      title="Agent Memory"
      badge={<Badge severity="info">{memories.length}</Badge>}
    >
      <StatsBar />

      <div className="space-y-2 flex-1 overflow-y-auto pr-1" style={{ minHeight: 0 }}>
        {sorted.map((memory) => {
          const isExpanded = expandedId === memory.id;
          const outcomeCfg = OUTCOME_CONFIG[memory.outcome] ?? OUTCOME_CONFIG.pending;
          const categoryLabel = CATEGORY_LABELS[memory.category] ?? memory.category;
          const agentColor = AGENT_COLORS[memory.agent_type] ?? '#58a6ff';

          return (
            <div
              key={memory.id}
              className="rounded-lg p-3 cursor-pointer transition-all duration-200"
              style={{
                background: 'var(--wr-bg-elevated)',
                border: '1px solid var(--wr-border)',
              }}
              onClick={() => setExpandedId(isExpanded ? null : memory.id)}
            >
              <div className="flex items-start gap-3">
                {/* Category badge */}
                <span
                  className="flex-shrink-0 text-[10px] font-semibold px-2 py-1 rounded mt-0.5"
                  style={{
                    background: `${agentColor}20`,
                    color: agentColor,
                    border: `1px solid ${agentColor}40`,
                  }}
                >
                  {categoryLabel}
                </span>

                <div className="flex-1 min-w-0">
                  <p
                    className="text-xs leading-relaxed"
                    style={{
                      color: 'var(--wr-text-primary)',
                      display: '-webkit-box',
                      WebkitLineClamp: isExpanded ? undefined : 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: isExpanded ? undefined : 'hidden',
                    }}
                  >
                    {memory.lesson}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    {/* Outcome */}
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wider"
                      style={{ color: outcomeCfg.color }}
                    >
                      {outcomeCfg.label}
                    </span>

                    {/* Region */}
                    {memory.affected_region && (
                      <span className="text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                        {memory.affected_region}
                      </span>
                    )}

                    {/* Occurrence count */}
                    {memory.occurrence_count > 1 && (
                      <span
                        className="text-[10px] font-mono-numbers"
                        style={{ color: 'var(--wr-text-muted)' }}
                      >
                        {memory.occurrence_count}x seen
                      </span>
                    )}

                    {/* Timestamp */}
                    <span className="text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                      {timeAgo(memory.created_at)}
                    </span>
                  </div>
                </div>

                <span className="text-xs flex-shrink-0" style={{ color: 'var(--wr-text-muted)' }}>
                  {isExpanded ? '\u25B2' : '\u25BC'}
                </span>
              </div>

              {/* Expanded detail */}
              {isExpanded && detail && (
                <div
                  className="mt-3 pt-3 animate-fade-in"
                  style={{ borderTop: '1px solid var(--wr-border)' }}
                >
                  <DetailField label="Situation">
                    <div
                      className="rounded p-2 whitespace-pre-wrap"
                      style={{
                        background: 'var(--wr-bg)',
                        border: '1px solid var(--wr-border)',
                      }}
                    >
                      {detail.situation}
                    </div>
                  </DetailField>

                  <DetailField label="Action Taken">
                    <div
                      className="rounded p-2 whitespace-pre-wrap"
                      style={{
                        background: 'var(--wr-bg)',
                        border: '1px solid var(--wr-border)',
                      }}
                    >
                      {detail.action_taken}
                    </div>
                  </DetailField>

                  <DetailField label="Lesson Learned">
                    <div
                      className="rounded p-2 whitespace-pre-wrap"
                      style={{
                        background: 'var(--wr-bg)',
                        border: '1px solid var(--wr-border)',
                        borderLeft: `3px solid ${outcomeCfg.color}`,
                      }}
                    >
                      {detail.lesson}
                    </div>
                  </DetailField>

                  <div className="flex gap-4 flex-wrap">
                    {detail.confidence_score != null && (
                      <DetailField label="Confidence">
                        <span
                          className="font-mono-numbers"
                          style={{
                            color:
                              detail.confidence_score >= 0.8
                                ? 'var(--wr-green)'
                                : detail.confidence_score >= 0.6
                                  ? 'var(--wr-amber)'
                                  : 'var(--wr-red)',
                          }}
                        >
                          {(detail.confidence_score * 100).toFixed(0)}%
                        </span>
                      </DetailField>
                    )}

                    {detail.cost_impact != null && (
                      <DetailField label="Cost Impact">
                        <span className="font-mono-numbers">
                          {new Intl.NumberFormat('en-US', {
                            style: 'currency',
                            currency: 'USD',
                            maximumFractionDigits: 0,
                          }).format(detail.cost_impact)}
                        </span>
                      </DetailField>
                    )}

                    {detail.time_impact_days != null && (
                      <DetailField label="Time Impact">
                        <span className="font-mono-numbers">
                          {detail.time_impact_days > 0 ? '+' : ''}
                          {detail.time_impact_days}d
                        </span>
                      </DetailField>
                    )}

                    {detail.risk_type && (
                      <DetailField label="Risk Type">{detail.risk_type}</DetailField>
                    )}

                    {detail.severity && (
                      <DetailField label="Severity">
                        <span className="uppercase">{detail.severity}</span>
                      </DetailField>
                    )}
                  </div>

                  <DetailField label="Recorded">
                    <span className="font-mono-numbers text-[11px]">
                      {new Date(detail.created_at).toLocaleString()}
                    </span>
                    {detail.last_referenced_at && (
                      <span className="ml-3 text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                        Last used: {timeAgo(detail.last_referenced_at)}
                      </span>
                    )}
                  </DetailField>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
