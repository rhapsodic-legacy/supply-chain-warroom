import { useState, useEffect, useRef } from 'react';
import { useDemoStore } from '../../stores/demoStore';
import { ExecutiveSummaryModal } from '../panels/ExecutiveSummaryModal';

interface StepNarrative {
  title: string;
  text: string | ((tier: string | null) => string);
}

const TIER_LABELS: Record<string, string> = {
  claude: 'Claude API (cloud)',
  gemma: 'Gemma 4 2B (local Ollama)',
  mock: 'simulated responses',
};

const STEP_NARRATIVES: Record<string, StepNarrative> = {
  start: {
    title: 'Demo Starting',
    text: 'Watch the war room respond to a critical supply chain disruption in real time.',
  },
  risk_created: {
    title: 'Risk Event Detected',
    text: 'A critical Suez Canal closure has been injected. The Risk Feed updates via Server-Sent Events in real time.',
  },
  triage_complete: {
    title: 'Automated Triage',
    text: 'The risk analysis pipeline scored all suppliers and flagged those with elevated exposure. No human intervention needed.',
  },
  simulation_running: {
    title: 'Monte Carlo Simulation',
    text: 'Running 10,000 iterations to model 90-day cost, delay, and fill-rate impact under the disruption scenario.',
  },
  simulation_complete: {
    title: 'Simulation Complete',
    text: 'Compare baseline vs. disrupted metrics. The engine uses real NumPy computation, not LLM-generated numbers.',
  },
  agents_deliberating: {
    title: 'AI Agents Deliberating',
    text: (tier) =>
      `The Orchestrator delegates to Risk Monitor, Simulation, and Strategy agents in sequence` +
      (tier ? ` — powered by ${TIER_LABELS[tier] || tier}.` : '.') +
      ' Watch the pipeline light up.',
  },
  mitigation_proposed: {
    title: 'Mitigation Proposed',
    text: 'The Strategy agent has recommended a three-pronged mitigation plan with cost-benefit analysis.',
  },
  approval_gate: {
    title: 'Human-in-the-Loop',
    text: 'The mitigation requires explicit human approval before execution. This is the governance checkpoint.',
  },
  complete: {
    title: 'Demo Complete',
    text: (tier) =>
      tier === 'mock'
        ? 'Demo complete. Risk events, triage, and simulation used real data. Agent responses were simulated.'
        : 'Every event was real data flowing through the system — actual API calls, real computation, and live SSE events.',
  },
};

export function DemoOverlay() {
  const currentStep = useDemoStore((s) => s.currentStep);
  const highlightedPanel = useDemoStore((s) => s.highlightedPanel);
  const isRunning = useDemoStore((s) => s.isRunning);
  const agentTier = useDemoStore((s) => s.agentTier);
  const simulationId = useDemoStore((s) => s.simulationId);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [showBrief, setShowBrief] = useState(false);

  // Scroll the highlighted panel into view
  useEffect(() => {
    if (!highlightedPanel) return;
    const el = document.getElementById(highlightedPanel);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedPanel]);

  // Reset brief modal when demo restarts
  useEffect(() => {
    if (isRunning && currentStep === 'start') setShowBrief(false);
  }, [isRunning, currentStep]);

  if (!currentStep || (!isRunning && currentStep !== 'complete')) return null;

  const narrative = STEP_NARRATIVES[currentStep];
  if (!narrative) return null;

  const text = typeof narrative.text === 'function' ? narrative.text(agentTier) : narrative.text;
  const canShowBrief = currentStep === 'complete' && simulationId;

  return (
    <>
      {/* Tooltip anchored to bottom-right */}
      <div ref={tooltipRef} className="demo-tooltip">
        <div className="demo-tooltip-header">
          <div className="demo-tooltip-dot" />
          <span className="demo-tooltip-title">{narrative.title}</span>
          {agentTier && currentStep === 'agents_deliberating' && (
            <span className="demo-tooltip-tier">{TIER_LABELS[agentTier] || agentTier}</span>
          )}
        </div>
        <p className="demo-tooltip-text">{text}</p>
        {canShowBrief && (
          <button
            className="demo-tooltip-brief-btn"
            onClick={() => setShowBrief(true)}
          >
            View Executive Brief
          </button>
        )}
      </div>

      {showBrief && simulationId && (
        <ExecutiveSummaryModal
          simulationId={simulationId}
          onClose={() => setShowBrief(false)}
        />
      )}
    </>
  );
}
