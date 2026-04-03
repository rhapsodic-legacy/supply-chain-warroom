import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { useDashboardStore } from '../../stores/dashboardStore';

/* Placeholder panels -- will be replaced with real widgets later */
function PlaceholderPanel({ name, className = '', style }: { name: string; className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`war-room-card flex items-center justify-center ${className}`}
      style={{ minHeight: 0, ...style }}
    >
      <span className="text-xs uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
        {name}
      </span>
    </div>
  );
}

export function WarRoomShell() {
  const sidebarOpen = useDashboardStore((s) => s.sidebarOpen);
  const toggleSidebar = useDashboardStore((s) => s.toggleSidebar);

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--wr-bg-primary)' }}>
      {/* Top Bar */}
      <header
        className="flex items-center justify-between px-4 flex-shrink-0"
        style={{
          height: '40px',
          background: 'var(--wr-bg-surface)',
          borderBottom: '1px solid var(--wr-border)',
        }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSidebar}
            className="text-sm px-1.5 py-0.5 rounded"
            style={{ color: 'var(--wr-text-secondary)', background: 'transparent' }}
            title="Toggle sidebar"
          >
            {sidebarOpen ? '\u25C0' : '\u25B6'}
          </button>
          <span
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: 'var(--wr-text-secondary)' }}
          >
            Supply Chain War Room
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono-numbers text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
            {new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC
          </span>
          <span className="inline-block w-2 h-2 rounded-full pulse-dot" style={{ background: 'var(--wr-green)' }} />
        </div>
      </header>

      {/* Main Area */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <Sidebar />

        {/* Content Grid */}
        <main className="flex-1 min-w-0 p-2 overflow-auto">
          <div
            className="grid gap-2 h-full"
            style={{
              gridTemplateColumns: '1fr 1fr 1fr',
              gridTemplateRows: '2fr 1fr 1fr 1fr',
              gridTemplateAreas: `
                "map map map"
                "risk suppliers orders"
                "demand demand agents"
                "sim sim agents"
              `,
            }}
          >
            <PlaceholderPanel name="Global Map" className="scanline-overlay" style={{ gridArea: 'map' }} />
            <PlaceholderPanel name="Risk Feed" style={{ gridArea: 'risk' }} />
            <PlaceholderPanel name="Supplier Grid" style={{ gridArea: 'suppliers' }} />
            <PlaceholderPanel name="Order Tracker" style={{ gridArea: 'orders' }} />
            <PlaceholderPanel name="Demand Chart" style={{ gridArea: 'demand' }} />
            <PlaceholderPanel name="Agent Log / Chat" style={{ gridArea: 'agents' }} />
            <PlaceholderPanel name="Simulation Panel" style={{ gridArea: 'sim' }} />
          </div>
        </main>
      </div>

      {/* Bottom Ticker */}
      <StatusBar />
    </div>
  );
}
