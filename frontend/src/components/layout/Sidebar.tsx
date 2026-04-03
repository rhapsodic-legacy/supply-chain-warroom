import { useDashboardStore } from '../../stores/dashboardStore';

const navItems = [
  { id: 'overview', label: 'Overview', icon: '\u25A3' },
  { id: 'risks', label: 'Risk Feed', icon: '\u26A0' },
  { id: 'suppliers', label: 'Suppliers', icon: '\u2302' },
  { id: 'orders', label: 'Orders', icon: '\u2B9E' },
  { id: 'demand', label: 'Demand', icon: '\u2261' },
  { id: 'simulations', label: 'Simulations', icon: '\u2699' },
  { id: 'agents', label: 'AI Agents', icon: '\u2731' },
];

export function Sidebar() {
  const { sidebarOpen, activePanel, setActivePanel } = useDashboardStore();

  if (!sidebarOpen) return null;

  return (
    <aside
      className="flex flex-col h-full overflow-y-auto"
      style={{
        width: '220px',
        background: 'var(--wr-bg-surface)',
        borderRight: '1px solid var(--wr-border)',
      }}
    >
      {/* Branding */}
      <div className="px-4 py-5" style={{ borderBottom: '1px solid var(--wr-border)' }}>
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded flex items-center justify-center text-xs font-bold font-mono-numbers"
            style={{
              background: 'var(--wr-cyan-dim)',
              color: 'var(--wr-cyan)',
              border: '1px solid rgba(88, 166, 255, 0.3)',
            }}
          >
            SC
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--wr-text-primary)' }}>
              War Room
            </p>
            <p className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
              Supply Chain
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 flex flex-col gap-0.5">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePanel(item.id)}
            className={`sidebar-item ${activePanel === item.id ? 'active' : ''}`}
          >
            <span className="text-base leading-none">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4" style={{ borderTop: '1px solid var(--wr-border)' }}>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full pulse-dot" style={{ background: 'var(--wr-green)' }} />
          <span className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
            System Online
          </span>
        </div>
      </div>
    </aside>
  );
}
