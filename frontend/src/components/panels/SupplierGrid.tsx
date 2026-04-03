import { useState, useMemo } from 'react';
import { Card } from '../shared/Card';
import { Badge } from '../shared/Badge';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useSuppliers } from '../../hooks/useSuppliers';


const countryFlags: Record<string, string> = {
  China: '\uD83C\uDDE8\uD83C\uDDF3',
  'United States': '\uD83C\uDDFA\uD83C\uDDF8',
  Germany: '\uD83C\uDDE9\uD83C\uDDEA',
  Japan: '\uD83C\uDDEF\uD83C\uDDF5',
  'South Korea': '\uD83C\uDDF0\uD83C\uDDF7',
  India: '\uD83C\uDDEE\uD83C\uDDF3',
  Taiwan: '\uD83C\uDDF9\uD83C\uDDFC',
  Vietnam: '\uD83C\uDDFB\uD83C\uDDF3',
  Mexico: '\uD83C\uDDF2\uD83C\uDDFD',
  Brazil: '\uD83C\uDDE7\uD83C\uDDF7',
  Thailand: '\uD83C\uDDF9\uD83C\uDDED',
  Indonesia: '\uD83C\uDDEE\uD83C\uDDE9',
  Malaysia: '\uD83C\uDDF2\uD83C\uDDFE',
  Turkey: '\uD83C\uDDF9\uD83C\uDDF7',
  UK: '\uD83C\uDDEC\uD83C\uDDE7',
  France: '\uD83C\uDDEB\uD83C\uDDF7',
  Italy: '\uD83C\uDDEE\uD83C\uDDF9',
  Canada: '\uD83C\uDDE8\uD83C\uDDE6',
  Australia: '\uD83C\uDDE6\uD83C\uDDFA',
};

function reliabilityColor(score: number): string {
  if (score >= 0.85) return 'var(--wr-green)';
  if (score >= 0.7) return 'var(--wr-amber)';
  return 'var(--wr-red)';
}

function activeSeverity(isActive: boolean): 'critical' | 'low' {
  return isActive ? 'low' : 'critical';
}

export function SupplierGrid({ className }: { className?: string }) {
  const { data: suppliers, isLoading, error } = useSuppliers();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sorted = useMemo(() => {
    if (!suppliers) return [];
    return [...suppliers].sort((a, b) => a.reliability_score - b.reliability_score);
  }, [suppliers]);

  if (isLoading) return <LoadingSpinner label="Loading suppliers..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!sorted.length) return <EmptyState message="No suppliers found" />;

  const selected = selectedId ? sorted.find((s) => s.id === selectedId) : null;

  return (
    <Card className={className} title="Supplier Health">
      {selected && (
        <div
          className="mb-4 p-3 rounded-lg animate-fade-in"
          style={{ background: 'var(--wr-bg-elevated)', border: '1px solid var(--wr-border-active)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">{countryFlags[selected.country] ?? '\uD83C\uDFF3\uFE0F'}</span>
              <span className="text-sm font-semibold" style={{ color: 'var(--wr-text-primary)' }}>
                {selected.name}
              </span>
            </div>
            <button
              className="text-xs px-2 py-1 rounded"
              style={{ color: 'var(--wr-text-muted)' }}
              onClick={() => setSelectedId(null)}
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span style={{ color: 'var(--wr-text-muted)' }}>Region</span>
              <p className="font-mono-numbers" style={{ color: 'var(--wr-text-secondary)' }}>{selected.region}</p>
            </div>
            <div>
              <span style={{ color: 'var(--wr-text-muted)' }}>City</span>
              <p className="font-mono-numbers" style={{ color: 'var(--wr-cyan)' }}>{selected.city}</p>
            </div>
            <div>
              <span style={{ color: 'var(--wr-text-muted)' }}>Lead Time</span>
              <p className="font-mono-numbers" style={{ color: 'var(--wr-text-secondary)' }}>{selected.base_lead_time_days}d</p>
            </div>
            <div>
              <span style={{ color: 'var(--wr-text-muted)' }}>Cost Multiplier</span>
              <p className="font-mono-numbers" style={{ color: 'var(--wr-amber)' }}>
                {selected.cost_multiplier.toFixed(2)}x
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[450px] overflow-y-auto pr-1">
        {sorted.map((supplier) => (
          <div
            key={supplier.id}
            className={`rounded-lg p-3 cursor-pointer transition-all duration-200 hover:scale-[1.02] ${
              !supplier.is_active ? 'glow-critical' : ''
            }`}
            style={{
              background: 'var(--wr-bg-elevated)',
              border: `1px solid ${selectedId === supplier.id ? 'var(--wr-cyan)' : 'var(--wr-border)'}`,
            }}
            onClick={() => setSelectedId(supplier.id === selectedId ? null : supplier.id)}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm flex-shrink-0">
                  {countryFlags[supplier.country] ?? '\uD83C\uDFF3\uFE0F'}
                </span>
                <span className="text-xs font-semibold truncate" style={{ color: 'var(--wr-text-primary)' }}>
                  {supplier.name}
                </span>
              </div>
              <Badge severity={activeSeverity(supplier.is_active)}>
                {supplier.is_active ? 'active' : 'inactive'}
              </Badge>
            </div>

            <div className="mt-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--wr-text-muted)' }}>
                  Reliability
                </span>
                <span
                  className="font-mono-numbers text-xs font-semibold"
                  style={{ color: reliabilityColor(supplier.reliability_score) }}
                >
                  {(supplier.reliability_score * 100).toFixed(0)}%
                </span>
              </div>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: 'var(--wr-bg-primary)' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${supplier.reliability_score * 100}%`,
                    background: reliabilityColor(supplier.reliability_score),
                  }}
                />
              </div>
            </div>

            <div className="flex items-center gap-3 mt-2 text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
              <span>{supplier.country}</span>
              <span className="font-mono-numbers">{supplier.capacity_units} units</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
