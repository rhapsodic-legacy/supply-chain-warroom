import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { useDashboardStore } from '../../stores/dashboardStore';
import { GlobalMap } from '../panels/GlobalMap';
import { RiskFeed } from '../panels/RiskFeed';
import { SupplierGrid } from '../panels/SupplierGrid';
import { OrderTracker } from '../panels/OrderTracker';
import { DemandChart } from '../panels/DemandChart';
import { AgentLog } from '../panels/AgentLog';
import { SimPanel } from '../panels/SimPanel';
import { ChatPanel } from '../panels/ChatPanel';

type Tab = 'agents' | 'chat';

function AgentChatTabs({ className, style }: { className?: string; style?: React.CSSProperties }) {
  const [tab, setTab] = useState<Tab>('agents');

  return (
    <div
      className={`flex flex-col ${className ?? ''}`}
      style={{ minHeight: 0, ...style }}
    >
      {/* Tab header */}
      <div
        className="flex flex-shrink-0"
        style={{
          borderBottom: '1px solid var(--wr-border)',
        }}
      >
        {(['agents', 'chat'] as Tab[]).map((t) => (
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
            {t === 'agents' ? 'Agent Log' : 'Chat'}
          </button>
        ))}
      </div>
      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {tab === 'agents' ? (
          <AgentLog className="h-full border-0 rounded-none" />
        ) : (
          <ChatPanel className="h-full border-0 rounded-none" />
        )}
      </div>
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
        {/* Sidebar */}
        <Sidebar />

        {/* Content Grid */}
        <main className="flex-1 min-w-0 p-2 overflow-hidden">
          <div
            className="grid gap-2 h-full"
            style={{
              gridTemplateColumns: '1fr 1fr 340px',
              gridTemplateRows: '1.8fr 1fr 1fr',
              gridTemplateAreas: `
                "map map agents"
                "risk suppliers agents"
                "demand orders sim"
              `,
            }}
          >
            <div style={{ gridArea: 'map' }} className="min-h-0 overflow-hidden">
              <GlobalMap className="h-full" />
            </div>
            <div style={{ gridArea: 'risk' }} className="min-h-0 overflow-hidden">
              <RiskFeed className="h-full" />
            </div>
            <div style={{ gridArea: 'suppliers' }} className="min-h-0 overflow-hidden">
              <SupplierGrid className="h-full" />
            </div>
            <div style={{ gridArea: 'orders' }} className="min-h-0 overflow-hidden">
              <OrderTracker className="h-full" />
            </div>
            <div style={{ gridArea: 'demand' }} className="min-h-0 overflow-hidden">
              <DemandChart className="h-full" />
            </div>
            <div
              style={{ gridArea: 'agents', background: 'var(--wr-bg-surface)', border: '1px solid var(--wr-border)', borderRadius: 'var(--wr-radius-lg)' }}
              className="min-h-0 overflow-hidden"
            >
              <AgentChatTabs />
            </div>
            <div style={{ gridArea: 'sim' }} className="min-h-0 overflow-hidden">
              <SimPanel className="h-full" />
            </div>
          </div>
        </main>
      </div>

      {/* Bottom Ticker */}
      <StatusBar />
    </div>
  );
}
