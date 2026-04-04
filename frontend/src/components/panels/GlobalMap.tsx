import { useState, useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Line,
  Marker,
} from 'react-simple-maps';
import { Card } from '../shared/Card';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorCard } from '../shared/ErrorCard';
import { EmptyState } from '../shared/EmptyState';
import { useRoutes } from '../../hooks/useRoutes';
import type { ShippingRoute } from '../../types/api';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

function riskColor(route: ShippingRoute): string {
  const score = route.risk_score;
  if (score > 0.6) return 'var(--wr-red)';
  if (score > 0.3) return 'var(--wr-amber)';
  return 'var(--wr-green)';
}

function statusLabel(isActive: boolean): string {
  return isActive ? 'ACTIVE' : 'INACTIVE';
}

interface TooltipData {
  x: number;
  y: number;
  route: ShippingRoute;
}

export function GlobalMap({ className }: { className?: string }) {
  const { data: routes, isLoading, error } = useRoutes();
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const endpoints = useMemo(() => {
    if (!routes) return [];
    const seen = new Set<string>();
    const pts: { coordinates: [number, number]; label: string }[] = [];
    for (const r of routes) {
      const originKey = `${r.origin_lon},${r.origin_lat}`;
      const destKey = `${r.dest_lon},${r.dest_lat}`;
      if (!seen.has(originKey)) {
        seen.add(originKey);
        pts.push({ coordinates: [r.origin_lon, r.origin_lat], label: r.origin_port });
      }
      if (!seen.has(destKey)) {
        seen.add(destKey);
        pts.push({ coordinates: [r.dest_lon, r.dest_lat], label: r.destination_port });
      }
    }
    return pts;
  }, [routes]);

  if (isLoading) return <LoadingSpinner label="Loading map..." />;
  if (error) return <ErrorCard message={(error as Error).message} />;
  if (!routes?.length) return <EmptyState message="No shipping routes" />;

  return (
    <Card className={className} title="Global Shipping Routes" noPadding>
      <div
        className="relative w-full overflow-hidden rounded-b-[10px]"
        style={{ background: '#070d15' }}
      >
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: 130, center: [20, 10] }}
          style={{ width: '100%', height: 'auto' }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#0d1117"
                  stroke="#1a2332"
                  strokeWidth={0.4}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none', fill: '#161d27' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {routes.map((route) => {
            const from: [number, number] = [route.origin_lon, route.origin_lat];
            const to: [number, number] = [route.dest_lon, route.dest_lat];
            return (
              <Line
                key={route.id}
                from={from}
                to={to}
                stroke={riskColor(route)}
                strokeWidth={route.is_active ? 1.6 : 1}
                strokeLinecap="round"
                strokeDasharray={!route.is_active ? '4 3' : undefined}
                style={{ opacity: 0.4 + route.risk_score * 0.6 }}
              />
            );
          })}

          {endpoints.map((pt) => (
            <Marker key={`${pt.coordinates[0]}-${pt.coordinates[1]}`} coordinates={pt.coordinates}>
              <circle r={3} fill="var(--wr-cyan)" opacity={0.85} />
              <circle r={5} fill="none" stroke="var(--wr-cyan)" strokeWidth={0.5} opacity={0.4} />
            </Marker>
          ))}

          {routes.map((route) => {
            const from: [number, number] = [route.origin_lon, route.origin_lat];
            const to: [number, number] = [route.dest_lon, route.dest_lat];
            const mid: [number, number] = [
              (from[0] + to[0]) / 2,
              (from[1] + to[1]) / 2,
            ];
            return (
              <Marker key={`hover-${route.id}`} coordinates={mid}>
                <circle
                  r={8}
                  fill="transparent"
                  cursor="pointer"
                  onMouseEnter={(e) => {
                    const rect = (e.target as SVGElement).closest('svg')?.getBoundingClientRect();
                    setTooltip({
                      x: e.clientX - (rect?.left ?? 0),
                      y: e.clientY - (rect?.top ?? 0),
                      route,
                    });
                  }}
                  onMouseLeave={() => setTooltip(null)}
                />
              </Marker>
            );
          })}
        </ComposableMap>

        {/* Risk level legend */}
        <div
          className="absolute bottom-3 left-3 z-10 flex items-center gap-3 px-2.5 py-1.5 rounded text-[10px]"
          style={{
            background: 'rgba(10, 14, 20, 0.85)',
            border: '1px solid var(--wr-border)',
            backdropFilter: 'blur(4px)',
          }}
        >
          <span className="uppercase tracking-wider font-semibold" style={{ color: 'var(--wr-text-muted)' }}>Risk</span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'var(--wr-green)' }} />
            <span style={{ color: 'var(--wr-green)' }}>Low</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'var(--wr-amber)' }} />
            <span style={{ color: 'var(--wr-amber)' }}>Med</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: 'var(--wr-red)' }} />
            <span style={{ color: 'var(--wr-red)' }}>High</span>
          </span>
        </div>

        {tooltip && (
          <div
            className="absolute z-10 pointer-events-none px-3 py-2 rounded-md text-xs"
            style={{
              left: tooltip.x + 10,
              top: tooltip.y - 10,
              background: 'var(--wr-bg-elevated)',
              border: '1px solid var(--wr-border-active)',
              color: 'var(--wr-text-primary)',
              maxWidth: 240,
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5), 0 0 1px rgba(88, 166, 255, 0.2)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <p className="font-semibold" style={{ color: riskColor(tooltip.route) }}>
              {tooltip.route.origin_port} &rarr; {tooltip.route.destination_port}
            </p>
            <div className="flex items-center gap-3 mt-1" style={{ color: 'var(--wr-text-secondary)' }}>
              <span className="font-mono-numbers">{tooltip.route.base_transit_days}d</span>
              <span className="font-mono-numbers">{tooltip.route.transport_mode.toUpperCase()}</span>
              <span
                className="font-mono-numbers"
                style={{ color: riskColor(tooltip.route) }}
              >
                Risk {(tooltip.route.risk_score * 100).toFixed(0)}%
              </span>
            </div>
            <span
              className="text-[10px] uppercase tracking-widest font-semibold mt-1 block"
              style={{ color: riskColor(tooltip.route) }}
            >
              {statusLabel(tooltip.route.is_active)}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}
