import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useDecisions, useDecisionDetail, useDecisionAction } from '../../hooks/useAgents';


const AGENT_COLORS: Record<string, string> = {
  risk_monitor: '#f85149',
  strategy: '#bc8cff',
  execution: '#58a6ff',
  simulation: '#3fb950',
};

const AGENT_LABELS: Record<string, string> = {
  risk_monitor: 'RSK',
  strategy: 'STR',
  execution: 'EXE',
  simulation: 'SIM',
};

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  proposed: { color: 'var(--wr-amber)', label: 'PROPOSED' },
  approved: { color: 'var(--wr-cyan)', label: 'APPROVED' },
  executed: { color: 'var(--wr-green)', label: 'EXECUTED' },
  rejected: { color: 'var(--wr-red)', label: 'REJECTED' },
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

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function tryParseJson(str: string): unknown {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

/** Renders a single key-value field in the audit detail */
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

/** Renders parsed JSON parameters as a mini key-value table */
function ParamsTable({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (!entries.length) return <span style={{ color: 'var(--wr-text-muted)' }}>none</span>;
  return (
    <div
      className="rounded p-2 space-y-1 font-mono text-[11px]"
      style={{ background: 'var(--wr-bg)', border: '1px solid var(--wr-border)' }}
    >
      {entries.map(([key, val]) => (
        <div key={key} className="flex gap-2">
          <span style={{ color: 'var(--wr-text-muted)' }}>{key}:</span>
          <span style={{ color: 'var(--wr-text-primary)' }}>
            {typeof val === 'object' ? JSON.stringify(val) : String(val)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AgentLog({ className }: { className?: string }) {
  const { data: decisions, isLoading, error } = useDecisions();
  const decisionAction = useDecisionAction();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { data: detail, isLoading: detailLoading } = useDecisionDetail(expandedId);

  if (isLoading) return <LoadingSpinner label="Loading agent log..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!decisions?.length) return <EmptyState message="No agent decisions" />;

  const sorted = [...decisions].sort(
    (a, b) => new Date(b.decided_at).getTime() - new Date(a.decided_at).getTime()
  );

  return (
    <Card className={className} title="Agent Decisions" badge={<Badge severity="info">{decisions.length}</Badge>}>
      <div className="space-y-2 flex-1 overflow-y-auto pr-1" style={{ minHeight: 0 }}>
        {sorted.map((decision) => {
          const isExpanded = expandedId === decision.id;
          const agentColor = AGENT_COLORS[decision.agent_type] ?? '#58a6ff';
          const agentLabel = AGENT_LABELS[decision.agent_type] ?? decision.agent_type.slice(0, 3).toUpperCase();
          const statusCfg = STATUS_CONFIG[decision.status] ?? STATUS_CONFIG.proposed;
          const isProposed = decision.status === 'proposed';
          const isPending = decisionAction.isPending && decisionAction.variables?.id === decision.id;

          return (
            <div
              key={decision.id}
              className="rounded-lg p-3 cursor-pointer transition-all duration-200"
              style={{
                background: 'var(--wr-bg-elevated)',
                border: isProposed
                  ? '1px solid var(--wr-amber)'
                  : '1px solid var(--wr-border)',
                boxShadow: isProposed ? '0 0 8px rgba(255, 180, 50, 0.15)' : undefined,
              }}
              onClick={() => setExpandedId(isExpanded ? null : decision.id)}
            >
              <div className="flex items-start gap-3">
                {/* Agent type badge */}
                <span
                  className="flex-shrink-0 text-[10px] font-mono-numbers font-bold px-2 py-1 rounded mt-0.5"
                  style={{
                    background: `${agentColor}20`,
                    color: agentColor,
                    border: `1px solid ${agentColor}40`,
                  }}
                >
                  {agentLabel}
                </span>

                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate" style={{ color: 'var(--wr-text-primary)' }}>
                    {decision.decision_summary}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    {/* Confidence */}
                    <span className="font-mono-numbers text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                      Conf:{' '}
                      <span
                        style={{
                          color: decision.confidence_score >= 0.8
                            ? 'var(--wr-green)'
                            : decision.confidence_score >= 0.6
                              ? 'var(--wr-amber)'
                              : 'var(--wr-red)',
                        }}
                      >
                        {(decision.confidence_score * 100).toFixed(0)}%
                      </span>
                    </span>

                    {/* Status */}
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wider"
                      style={{ color: statusCfg.color }}
                    >
                      {statusCfg.label}
                    </span>

                    {/* Timestamp */}
                    <span className="text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                      {timeAgo(decision.decided_at)}
                    </span>
                  </div>
                </div>

                <span className="text-xs flex-shrink-0" style={{ color: 'var(--wr-text-muted)' }}>
                  {isExpanded ? '\u25B2' : '\u25BC'}
                </span>
              </div>

              {/* --- Expanded audit detail --- */}
              {isExpanded && (
                <div className="mt-3 pt-3 animate-fade-in" style={{ borderTop: '1px solid var(--wr-border)' }}>
                  {detailLoading ? (
                    <div className="py-2 text-center text-xs" style={{ color: 'var(--wr-text-muted)' }}>
                      Loading detail...
                    </div>
                  ) : detail ? (
                    <>
                      <DetailField label="Decision Type">
                        {detail.decision_type.replace(/_/g, ' ')}
                      </DetailField>

                      <DetailField label="Agent Reasoning">
                        <div
                          className="rounded p-2 whitespace-pre-wrap"
                          style={{
                            background: 'var(--wr-bg)',
                            border: '1px solid var(--wr-border)',
                            maxHeight: '120px',
                            overflowY: 'auto',
                          }}
                        >
                          {detail.reasoning}
                        </div>
                      </DetailField>

                      {/* Parameters */}
                      {detail.parameters && detail.parameters !== '{}' && (
                        <DetailField label="Parameters">
                          {(() => {
                            const parsed = tryParseJson(detail.parameters);
                            return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (
                              <ParamsTable data={parsed as Record<string, unknown>} />
                            ) : (
                              <span>{detail.parameters}</span>
                            );
                          })()}
                        </DetailField>
                      )}

                      {/* Impact metrics */}
                      {(detail.cost_impact != null || detail.time_impact_days != null) && (
                        <DetailField label="Impact Assessment">
                          <div className="flex gap-4">
                            {detail.cost_impact != null && (
                              <span className="font-mono-numbers">
                                Cost:{' '}
                                <span style={{ color: detail.cost_impact > 0 ? 'var(--wr-red)' : 'var(--wr-green)' }}>
                                  {detail.cost_impact > 0 ? '+' : ''}{formatCurrency(detail.cost_impact)}
                                </span>
                              </span>
                            )}
                            {detail.time_impact_days != null && (
                              <span className="font-mono-numbers">
                                Time:{' '}
                                <span style={{ color: detail.time_impact_days > 0 ? 'var(--wr-amber)' : 'var(--wr-green)' }}>
                                  {detail.time_impact_days > 0 ? '+' : ''}{detail.time_impact_days}d
                                </span>
                              </span>
                            )}
                          </div>
                        </DetailField>
                      )}

                      {/* Affected orders */}
                      {detail.affected_orders && detail.affected_orders !== '[]' && (
                        <DetailField label="Affected Orders">
                          {(() => {
                            const parsed = tryParseJson(detail.affected_orders);
                            if (Array.isArray(parsed) && parsed.length > 0) {
                              return (
                                <span className="font-mono text-[11px]">
                                  {parsed.length} order{parsed.length !== 1 ? 's' : ''}: {parsed.slice(0, 3).join(', ')}
                                  {parsed.length > 3 ? ` +${parsed.length - 3} more` : ''}
                                </span>
                              );
                            }
                            return <span>{detail.affected_orders}</span>;
                          })()}
                        </DetailField>
                      )}

                      {/* Trigger event */}
                      {detail.trigger_event_id && (
                        <DetailField label="Triggered By">
                          <span className="font-mono text-[11px]">{detail.trigger_event_id}</span>
                        </DetailField>
                      )}

                      {/* Outcome notes */}
                      {detail.outcome_notes && (
                        <DetailField label="Reviewer Notes">
                          <span style={{ color: 'var(--wr-text-primary)' }}>{detail.outcome_notes}</span>
                        </DetailField>
                      )}

                      {/* Timeline */}
                      <DetailField label="Timeline">
                        <div className="flex gap-4 font-mono-numbers text-[11px]">
                          <span>Decided: {new Date(detail.decided_at).toLocaleString()}</span>
                          {detail.executed_at && (
                            <span>Executed: {new Date(detail.executed_at).toLocaleString()}</span>
                          )}
                        </div>
                      </DetailField>
                    </>
                  ) : (
                    <DetailField label="Decision Type">
                      {decision.decision_type}
                    </DetailField>
                  )}

                  {/* Approve / Reject buttons for proposed decisions */}
                  {isProposed && (
                    <div className="flex gap-2 mt-3">
                      <button
                        className="flex-1 py-1.5 px-3 rounded text-xs font-semibold uppercase tracking-wider transition-all duration-200 disabled:opacity-50"
                        style={{
                          background: 'rgba(63, 185, 80, 0.15)',
                          color: 'var(--wr-green)',
                          border: '1px solid rgba(63, 185, 80, 0.4)',
                        }}
                        disabled={isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          decisionAction.mutate({ id: decision.id, action: 'approve' });
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(63, 185, 80, 0.3)';
                          e.currentTarget.style.boxShadow = '0 0 12px rgba(63, 185, 80, 0.3)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(63, 185, 80, 0.15)';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      >
                        {isPending && decisionAction.variables?.action === 'approve' ? 'Approving...' : 'Approve'}
                      </button>
                      <button
                        className="flex-1 py-1.5 px-3 rounded text-xs font-semibold uppercase tracking-wider transition-all duration-200 disabled:opacity-50"
                        style={{
                          background: 'rgba(248, 81, 73, 0.15)',
                          color: 'var(--wr-red)',
                          border: '1px solid rgba(248, 81, 73, 0.4)',
                        }}
                        disabled={isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          decisionAction.mutate({ id: decision.id, action: 'reject' });
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(248, 81, 73, 0.3)';
                          e.currentTarget.style.boxShadow = '0 0 12px rgba(248, 81, 73, 0.3)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(248, 81, 73, 0.15)';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                      >
                        {isPending && decisionAction.variables?.action === 'reject' ? 'Rejecting...' : 'Reject'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
