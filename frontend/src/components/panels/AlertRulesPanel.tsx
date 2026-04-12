import { useState } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import {
  useAlertRules,
  useAlertRuleDetail,
  useCreateAlertRule,
  useToggleAlertRule,
  useDeleteAlertRule,
  useEvaluateRules,
} from '../../hooks/useAlertRules';
import type { AlertRuleCreate } from '../../types/api';

const METRIC_LABELS: Record<string, string> = {
  supplier_reliability: 'Supplier Reliability',
  risk_event_count: 'Risk Event Count',
  order_delay_days: 'Order Delay (days)',
  composite_risk_score: 'Composite Risk Score',
  regional_risk_density: 'Regional Risk Density',
};

const OPERATOR_LABELS: Record<string, string> = {
  lt: '<',
  lte: '\u2264',
  gt: '>',
  gte: '\u2265',
  eq: '=',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'var(--wr-red)',
  high: '#f0883e',
  medium: 'var(--wr-amber)',
  low: 'var(--wr-green)',
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

function CreateRuleForm({ onClose }: { onClose: () => void }) {
  const createRule = useCreateAlertRule();
  const [form, setForm] = useState<AlertRuleCreate>({
    name: '',
    metric: 'supplier_reliability',
    operator: 'lt',
    threshold: 0.7,
    severity: 'high',
    trigger_agent_analysis: true,
    cooldown_minutes: 60,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    createRule.mutate(form, {
      onSuccess: () => onClose(),
    });
  };

  const inputStyle = {
    background: 'var(--wr-bg)',
    border: '1px solid var(--wr-border)',
    color: 'var(--wr-text-primary)',
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 rounded-lg space-y-3"
      style={{ background: 'var(--wr-bg-elevated)', border: '1px solid var(--wr-cyan)', boxShadow: '0 0 8px rgba(88, 166, 255, 0.15)' }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--wr-cyan)' }}>
          New Alert Rule
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-xs px-2 py-0.5 rounded"
          style={{ color: 'var(--wr-text-muted)' }}
        >
          Cancel
        </button>
      </div>

      <input
        type="text"
        placeholder="Rule name..."
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
        className="w-full text-xs rounded px-2 py-1.5"
        style={inputStyle}
        required
      />

      <div className="grid grid-cols-3 gap-2">
        <select
          value={form.metric}
          onChange={(e) => setForm({ ...form, metric: e.target.value })}
          className="text-[11px] rounded px-2 py-1.5"
          style={inputStyle}
        >
          {Object.entries(METRIC_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>

        <select
          value={form.operator}
          onChange={(e) => setForm({ ...form, operator: e.target.value })}
          className="text-[11px] rounded px-2 py-1.5"
          style={inputStyle}
        >
          <option value="lt">{'< less than'}</option>
          <option value="lte">{'\u2264 at or below'}</option>
          <option value="gt">{'> greater than'}</option>
          <option value="gte">{'\u2265 at or above'}</option>
          <option value="eq">{'= equals'}</option>
        </select>

        <input
          type="number"
          step="any"
          value={form.threshold}
          onChange={(e) => setForm({ ...form, threshold: parseFloat(e.target.value) || 0 })}
          className="text-[11px] rounded px-2 py-1.5 font-mono-numbers"
          style={inputStyle}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <select
          value={form.severity}
          onChange={(e) => setForm({ ...form, severity: e.target.value })}
          className="text-[11px] rounded px-2 py-1.5"
          style={inputStyle}
        >
          <option value="low">Low severity</option>
          <option value="medium">Medium severity</option>
          <option value="high">High severity</option>
          <option value="critical">Critical severity</option>
        </select>

        <label className="flex items-center gap-2 text-[11px]" style={{ color: 'var(--wr-text-secondary)' }}>
          <input
            type="checkbox"
            checked={form.trigger_agent_analysis}
            onChange={(e) => setForm({ ...form, trigger_agent_analysis: e.target.checked })}
          />
          Trigger agent analysis
        </label>
      </div>

      <input
        type="text"
        placeholder="Region filter (optional)"
        value={form.filter_region || ''}
        onChange={(e) => setForm({ ...form, filter_region: e.target.value || undefined })}
        className="w-full text-[11px] rounded px-2 py-1.5"
        style={inputStyle}
      />

      <button
        type="submit"
        disabled={createRule.isPending || !form.name.trim()}
        className="w-full py-1.5 rounded text-xs font-semibold uppercase tracking-wider transition-all disabled:opacity-50"
        style={{
          background: 'rgba(88, 166, 255, 0.15)',
          color: 'var(--wr-cyan)',
          border: '1px solid rgba(88, 166, 255, 0.4)',
        }}
      >
        {createRule.isPending ? 'Creating...' : 'Create Rule'}
      </button>
    </form>
  );
}

export function AlertRulesPanel({ className }: { className?: string }) {
  const { data: rules, isLoading, error } = useAlertRules();
  const toggleRule = useToggleAlertRule();
  const deleteRule = useDeleteAlertRule();
  const evaluateRules = useEvaluateRules();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const { data: detail } = useAlertRuleDetail(expandedId);

  if (isLoading) return <LoadingSpinner label="Loading alert rules..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;

  const enabledCount = rules?.filter((r) => r.is_enabled).length ?? 0;

  return (
    <Card
      className={className}
      title="Alert Rules"
      badge={
        <div className="flex items-center gap-2">
          <Badge severity="info">{enabledCount} active</Badge>
          <button
            onClick={() => evaluateRules.mutate()}
            disabled={evaluateRules.isPending}
            className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded transition-all"
            style={{
              background: 'rgba(63, 185, 80, 0.15)',
              color: 'var(--wr-green)',
              border: '1px solid rgba(63, 185, 80, 0.3)',
            }}
          >
            {evaluateRules.isPending ? 'Running...' : 'Evaluate'}
          </button>
        </div>
      }
    >
      {/* Create button */}
      {!showCreate && (
        <button
          onClick={() => setShowCreate(true)}
          className="w-full mb-2 py-1.5 rounded text-xs font-semibold uppercase tracking-wider transition-all"
          style={{
            background: 'rgba(88, 166, 255, 0.1)',
            color: 'var(--wr-cyan)',
            border: '1px dashed rgba(88, 166, 255, 0.3)',
          }}
        >
          + New Rule
        </button>
      )}

      {showCreate && <CreateRuleForm onClose={() => setShowCreate(false)} />}

      {/* Rules list */}
      {!rules?.length && !showCreate ? (
        <EmptyState message="No alert rules defined" />
      ) : (
        <div className="space-y-2 flex-1 overflow-y-auto pr-1 mt-2" style={{ minHeight: 0 }}>
          {rules?.map((rule) => {
            const isExpanded = expandedId === rule.id;
            const sevColor = SEVERITY_COLORS[rule.severity] ?? 'var(--wr-amber)';
            const metricLabel = METRIC_LABELS[rule.metric] ?? rule.metric;
            const opLabel = OPERATOR_LABELS[rule.operator] ?? rule.operator;

            return (
              <div
                key={rule.id}
                className="rounded-lg p-3 cursor-pointer transition-all duration-200"
                style={{
                  background: 'var(--wr-bg-elevated)',
                  border: '1px solid var(--wr-border)',
                  opacity: rule.is_enabled ? 1 : 0.5,
                }}
                onClick={() => setExpandedId(isExpanded ? null : rule.id)}
              >
                <div className="flex items-start gap-3">
                  {/* Severity dot */}
                  <span
                    className="flex-shrink-0 w-2 h-2 rounded-full mt-1.5"
                    style={{ background: sevColor }}
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p
                        className="text-xs font-medium truncate"
                        style={{ color: 'var(--wr-text-primary)' }}
                      >
                        {rule.name}
                      </p>
                      {!rule.is_enabled && (
                        <span
                          className="text-[9px] uppercase px-1 rounded"
                          style={{ background: 'var(--wr-bg)', color: 'var(--wr-text-muted)' }}
                        >
                          disabled
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className="text-[10px] font-mono-numbers px-1.5 py-0.5 rounded"
                        style={{
                          background: 'var(--wr-bg)',
                          color: 'var(--wr-text-secondary)',
                        }}
                      >
                        {metricLabel} {opLabel} {rule.threshold}
                      </span>

                      {rule.trigger_count > 0 && (
                        <span
                          className="text-[10px] font-mono-numbers"
                          style={{ color: 'var(--wr-text-muted)' }}
                        >
                          {rule.trigger_count}x fired
                        </span>
                      )}

                      {rule.last_triggered_at && (
                        <span className="text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
                          {timeAgo(rule.last_triggered_at)}
                        </span>
                      )}
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
                    {detail.description && (
                      <p
                        className="text-xs mb-2 leading-relaxed"
                        style={{ color: 'var(--wr-text-secondary)' }}
                      >
                        {detail.description}
                      </p>
                    )}

                    <div className="flex gap-4 flex-wrap text-[10px] mb-3" style={{ color: 'var(--wr-text-muted)' }}>
                      <span>Cooldown: {detail.cooldown_minutes}m</span>
                      <span>Agent analysis: {detail.trigger_agent_analysis ? 'yes' : 'no'}</span>
                      {detail.filter_region && <span>Region: {detail.filter_region}</span>}
                      {detail.filter_severity && <span>Severity: {detail.filter_severity}</span>}
                      <span>Created: {new Date(detail.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="flex gap-2">
                      <button
                        className="flex-1 py-1.5 rounded text-[10px] font-semibold uppercase tracking-wider transition-all"
                        style={{
                          background: rule.is_enabled
                            ? 'rgba(255, 180, 50, 0.15)'
                            : 'rgba(63, 185, 80, 0.15)',
                          color: rule.is_enabled ? 'var(--wr-amber)' : 'var(--wr-green)',
                          border: rule.is_enabled
                            ? '1px solid rgba(255, 180, 50, 0.3)'
                            : '1px solid rgba(63, 185, 80, 0.3)',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleRule.mutate(rule.id);
                        }}
                      >
                        {rule.is_enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        className="py-1.5 px-3 rounded text-[10px] font-semibold uppercase tracking-wider transition-all"
                        style={{
                          background: 'rgba(248, 81, 73, 0.15)',
                          color: 'var(--wr-red)',
                          border: '1px solid rgba(248, 81, 73, 0.3)',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteRule.mutate(rule.id);
                          setExpandedId(null);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
