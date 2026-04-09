import { useState, useRef } from 'react';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { useDashboardStore } from '../../stores/dashboardStore';
import { GlobalMap } from '../panels/GlobalMap';
import { RiskFeed } from '../panels/RiskFeed';
import { SupplierGrid } from '../panels/SupplierGrid';
import { OrderTracker } from '../panels/OrderTracker';
import { DemandChart } from '../panels/DemandChart';
import { AgentLog } from '../panels/AgentLog';
import { AgentPipeline } from '../panels/AgentPipeline';
import { SimPanel } from '../panels/SimPanel';
import { ChatPanel } from '../panels/ChatPanel';

type Tab = 'pipeline' | 'agents' | 'chat';

const TAB_LABELS: Record<Tab, string> = {
  pipeline: 'Pipeline',
  agents: 'Agent Log',
  chat: 'Chat',
};

function AgentChatTabs({ className, style }: { className?: string; style?: React.CSSProperties }) {
  const [tab, setTab] = useState<Tab>('pipeline');

  return (
    <div
      className={`flex flex-col ${className ?? ''}`}
      style={{ minHeight: 0, ...style }}
    >
      <div
        className="flex flex-shrink-0"
        style={{ borderBottom: '1px solid var(--wr-border)' }}
      >
        {(['pipeline', 'agents', 'chat'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="flex-1 text-[11px] font-semibold uppercase tracking-wider py-2 transition-colors"
            style={{
              color: tab === t ? 'var(--wr-cyan)' : 'var(--wr-text-muted)',
              background: tab === t ? 'var(--wr-cyan-dim)' : 'transparent',
              borderBottom: tab === t ? '2px solid var(--wr-cyan)' : '2px solid transparent',
            }}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        {tab === 'pipeline' ? (
          <AgentPipeline className="h-full border-0 rounded-none" />
        ) : tab === 'agents' ? (
          <AgentLog className="h-full border-0 rounded-none" />
        ) : (
          <ChatPanel className="h-full border-0 rounded-none" />
        )}
      </div>
    </div>
  );
}

/** Section IDs the sidebar can scroll to */
const SECTION_IDS: Record<string, string> = {
  overview: 'section-map',
  risks: 'section-risk',
  suppliers: 'section-suppliers',
  orders: 'section-orders',
  demand: 'section-demand',
  simulations: 'section-sim',
  agents: 'section-agents',
};

export function WarRoomShell() {
  const sidebarOpen = useDashboardStore((s) => s.sidebarOpen);
  const toggleSidebar = useDashboardStore((s) => s.toggleSidebar);
  const mainRef = useRef<HTMLElement>(null);

  // Override setActivePanel to also scroll to the section
  const originalSetActive = useDashboardStore.getState().setActivePanel;
  useDashboardStore.setState({
    setActivePanel: (id: string) => {
      originalSetActive(id);
      const sectionId = SECTION_IDS[id];
      if (sectionId) {
        setTimeout(() => {
          const el = document.getElementById(sectionId);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 50);
      }
    },
  });

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--wr-bg-primary)' }}>
      {/* Top Bar */}
      <header
        className="flex items-center justify-between px-4 flex-shrink-0"
        style={{
          height: '44px',
          background: 'var(--wr-bg-surface)',
          borderBottom: '1px solid var(--wr-border)',
        }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSidebar}
            className="text-sm px-1.5 py-0.5 rounded hover:bg-[var(--wr-bg-elevated)] transition-colors"
            style={{ color: 'var(--wr-text-secondary)', background: 'transparent' }}
            title="Toggle sidebar"
          >
            {sidebarOpen ? '\u25C0' : '\u25B6'}
          </button>
          <div className="flex items-center gap-2">
            <div
              className="w-6 h-6 rounded flex items-center justify-center"
              style={{
                background: 'var(--wr-cyan-dim)',
                border: '1px solid rgba(88, 166, 255, 0.3)',
              }}
            >
              <span className="text-[10px] font-bold font-mono-numbers" style={{ color: 'var(--wr-cyan)' }}>
                SC
              </span>
            </div>
            <span
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: 'var(--wr-text-primary)' }}
            >
              Supply Chain War Room
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full pulse-dot" style={{ background: 'var(--wr-green)' }} />
            <span className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
              Live
            </span>
          </div>
          <span className="font-mono-numbers text-[10px]" style={{ color: 'var(--wr-text-muted)' }}>
            {new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC
          </span>
        </div>
      </header>

      {/* Main Area */}
      <div className="flex flex-1 min-h-0">
        <Sidebar />

        {/*
          Scrollable content — NO fixed heights on rows.
          Panels auto-size to their content. The main area scrolls.
          This guarantees no panel is ever clipped regardless of content.
        */}
        <main ref={mainRef} className="flex-1 min-w-0 p-2 overflow-y-auto">
          {/* Row 1: Map + Agent panel */}
          <div id="section-map" className="grid gap-2 mb-2" style={{ gridTemplateColumns: '1fr 340px' }}>
            <div style={{ minHeight: '380px' }}>
              <GlobalMap className="h-full" />
            </div>
            <div
              style={{
                minHeight: '380px',
                maxHeight: '500px',
                background: 'var(--wr-bg-surface)',
                border: '1px solid var(--wr-border)',
                borderRadius: 'var(--wr-radius-lg)',
              }}
              id="section-agents"
            >
              <AgentChatTabs className="h-full" />
            </div>
          </div>

          {/* Row 2: Risk + Suppliers */}
          <div className="grid gap-2 mb-2 items-start" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div id="section-risk">
              <RiskFeed />
            </div>
            <div id="section-suppliers">
              <SupplierGrid />
            </div>
          </div>

          {/* Row 3: Demand + Orders + Simulation */}
          <div className="grid gap-2 mb-2 items-start" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <div id="section-demand">
              <DemandChart />
            </div>
            <div id="section-orders">
              <OrderTracker />
            </div>
            <div id="section-sim">
              <SimPanel />
            </div>
          </div>
        </main>
      </div>

      {/* Bottom Ticker */}
      <StatusBar />
    </div>
  );
}
