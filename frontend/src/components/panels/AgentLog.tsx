import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useDecisions, useDecisionAction } from '../../hooks/useAgents';


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

export function AgentLog({ className }: { className?: string }) {
  const { data: decisions, isLoading, error } = useDecisions();
  const decisionAction = useDecisionAction();
  const [expandedId, setExpandedId] = useState<string | null>(null);

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

              {isExpanded && (
                <div className="mt-3 pt-3 animate-fade-in" style={{ borderTop: '1px solid var(--wr-border)' }}>
                  <div className="mb-2">
                    <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
                      Decision Type
                    </span>
                    <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--wr-text-secondary)' }}>
                      {decision.decision_type}
                    </p>
                  </div>

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
