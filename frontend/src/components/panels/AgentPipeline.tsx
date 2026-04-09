import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useHandoffSessions } from '../../hooks/useHandoffs';
import type { AgentHandoff, AgentHandoffSession } from '../../types/api';

const AGENT_META: Record<string, { label: string; color: string; short: string }> = {
  orchestrator: { label: 'Orchestrator', color: '#58a6ff', short: 'ORC' },
  risk_monitor: { label: 'Risk Monitor', color: '#f85149', short: 'RSK' },
  simulation: { label: 'Simulation', color: '#3fb950', short: 'SIM' },
  strategy: { label: 'Strategy', color: '#bc8cff', short: 'STR' },
  execution: { label: 'Execution', color: '#58a6ff', short: 'EXE' },
};

function agentMeta(name: string) {
  return AGENT_META[name] ?? { label: name, color: '#8b949e', short: name.slice(0, 3).toUpperCase() };
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/** A single agent node in the pipeline */
function AgentNode({
  agent,
  status,
  durationMs,
}: {
  agent: string;
  status: 'running' | 'completed' | 'error' | 'idle';
  durationMs?: number | null;
}) {
  const meta = agentMeta(agent);
  const isRunning = status === 'running';
  const isError = status === 'error';
  const isCompleted = status === 'completed';

  return (
    <div
      className="flex flex-col items-center gap-1"
      style={{ minWidth: '56px' }}
    >
      <div
        className={`relative w-10 h-10 rounded-lg flex items-center justify-center text-[10px] font-bold font-mono-numbers transition-all duration-300 ${isRunning ? 'pipeline-node-active' : ''}`}
        style={{
          background: isCompleted
            ? `${meta.color}25`
            : isRunning
              ? `${meta.color}40`
              : isError
                ? 'rgba(248, 81, 73, 0.2)'
                : 'var(--wr-bg-elevated)',
          border: `1.5px solid ${
            isCompleted ? meta.color : isRunning ? meta.color : isError ? 'var(--wr-red)' : 'var(--wr-border)'
          }`,
          color: isCompleted || isRunning ? meta.color : isError ? 'var(--wr-red)' : 'var(--wr-text-muted)',
          boxShadow: isRunning
            ? `0 0 12px ${meta.color}50, 0 0 4px ${meta.color}30`
            : isCompleted
              ? `0 0 6px ${meta.color}20`
              : 'none',
        }}
      >
        {meta.short}
        {isRunning && (
          <span
            className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full pulse-dot"
            style={{ background: meta.color }}
          />
        )}
      </div>
      <span
        className="text-[9px] leading-tight text-center"
        style={{ color: isCompleted || isRunning ? 'var(--wr-text-secondary)' : 'var(--wr-text-muted)' }}
      >
        {meta.label}
      </span>
      {durationMs != null && (
        <span className="text-[9px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
          {formatMs(durationMs)}
        </span>
      )}
    </div>
  );
}

/** Animated connector arrow between nodes */
function Connector({ active, completed }: { active: boolean; completed: boolean }) {
  return (
    <div className="flex items-center self-start" style={{ marginTop: '14px', width: '28px' }}>
      <div
        className={`h-[1.5px] flex-1 transition-all duration-500 ${active ? 'pipeline-connector-active' : ''}`}
        style={{
          background: completed
            ? 'var(--wr-cyan)'
            : active
              ? 'var(--wr-cyan)'
              : 'var(--wr-border)',
          opacity: completed ? 0.6 : active ? 1 : 0.4,
        }}
      />
      <div
        className="w-0 h-0 flex-shrink-0"
        style={{
          borderTop: '3px solid transparent',
          borderBottom: '3px solid transparent',
          borderLeft: `5px solid ${completed || active ? 'var(--wr-cyan)' : 'var(--wr-border)'}`,
          opacity: completed ? 0.6 : active ? 1 : 0.4,
        }}
      />
    </div>
  );
}

/** Pipeline view for a single session */
function SessionPipeline({ session }: { session: AgentHandoffSession }) {
  const [expanded, setExpanded] = useState(false);
  const hasRunning = session.handoffs.some((h) => h.status === 'running');
  const hasError = session.handoffs.some((h) => h.status === 'error');

  // Build unique agent sequence: orchestrator → each to_agent in order
  const agents = ['orchestrator', ...session.handoffs.map((h) => h.to_agent)];

  // Map agent to its handoff status
  const handoffByAgent = new Map<string, AgentHandoff>();
  for (const h of session.handoffs) {
    handoffByAgent.set(h.to_agent, h);
  }

  return (
    <div
      className="rounded-lg p-3 cursor-pointer transition-all duration-200"
      style={{
        background: 'var(--wr-bg-elevated)',
        border: hasRunning
          ? '1px solid var(--wr-cyan)'
          : hasError
            ? '1px solid var(--wr-red)'
            : '1px solid var(--wr-border)',
        boxShadow: hasRunning ? '0 0 10px rgba(88, 166, 255, 0.15)' : undefined,
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
            {timeAgo(session.started_at)}
          </span>
          {hasRunning && (
            <span
              className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
              style={{ background: 'var(--wr-cyan-dim)', color: 'var(--wr-cyan)' }}
            >
              LIVE
            </span>
          )}
          {!hasRunning && session.total_duration_ms != null && (
            <span className="text-[10px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
              {formatMs(session.total_duration_ms)} total
            </span>
          )}
        </div>
        <span className="text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
          {session.handoffs.length} handoff{session.handoffs.length !== 1 ? 's' : ''}
          {' '}{expanded ? '\u25B2' : '\u25BC'}
        </span>
      </div>

      {/* Pipeline visualization */}
      <div className="flex items-start gap-0 overflow-x-auto pb-1">
        {agents.map((agent, idx) => {
          const handoff = handoffByAgent.get(agent);
          const isOrchestrator = idx === 0;

          // Orchestrator is always "completed" if there are handoffs
          const status: 'running' | 'completed' | 'error' | 'idle' = isOrchestrator
            ? 'completed'
            : handoff?.status ?? 'idle';

          return (
            <div key={`${agent}-${idx}`} className="flex items-start">
              {idx > 0 && (
                <Connector
                  active={handoff?.status === 'running'}
                  completed={handoff?.status === 'completed'}
                />
              )}
              <AgentNode
                agent={agent}
                status={status}
                durationMs={handoff?.duration_ms}
              />
            </div>
          );
        })}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-3 pt-3 space-y-2 animate-fade-in" style={{ borderTop: '1px solid var(--wr-border)' }}>
          {session.handoffs.map((h) => {
            const meta = agentMeta(h.to_agent);
            return (
              <div
                key={h.id}
                className="flex items-start gap-3 p-2 rounded"
                style={{ background: 'var(--wr-bg-surface)' }}
              >
                <span
                  className="text-[9px] font-mono-numbers font-bold px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5"
                  style={{
                    background: `${meta.color}20`,
                    color: meta.color,
                    border: `1px solid ${meta.color}40`,
                  }}
                >
                  {meta.short}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] truncate" style={{ color: 'var(--wr-text-primary)' }}>
                    {h.query}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span
                      className="text-[9px] font-semibold uppercase"
                      style={{
                        color:
                          h.status === 'completed'
                            ? 'var(--wr-green)'
                            : h.status === 'running'
                              ? 'var(--wr-cyan)'
                              : 'var(--wr-red)',
                      }}
                    >
                      {h.status}
                    </span>
                    {h.duration_ms != null && (
                      <span className="text-[9px] font-mono-numbers" style={{ color: 'var(--wr-text-muted)' }}>
                        {formatMs(h.duration_ms)}
                      </span>
                    )}
                  </div>
                  {h.result_summary && (
                    <p
                      className="text-[10px] mt-1 line-clamp-2"
                      style={{ color: 'var(--wr-text-muted)' }}
                    >
                      {h.result_summary}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AgentPipeline({ className }: { className?: string }) {
  const { data: sessions, isLoading, error } = useHandoffSessions();

  if (isLoading) return <LoadingSpinner label="Loading pipeline..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!sessions?.length) {
    return (
      <EmptyState message="No agent handoffs yet. Start a chat to see the pipeline." />
    );
  }

  return (
    <Card
      className={className}
      title="Agent Pipeline"
      badge={<Badge severity="info">{sessions.length}</Badge>}
    >
      <div className="space-y-2 flex-1 overflow-y-auto pr-1" style={{ minHeight: 0 }}>
        {sessions.map((session) => (
          <SessionPipeline key={session.session_id} session={session} />
        ))}
      </div>
    </Card>
  );
}
