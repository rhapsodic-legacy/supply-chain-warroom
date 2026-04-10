import { useDemoStore } from '../../stores/demoStore';

const STEP_LABELS: Record<string, string> = {
  start: 'Initializing',
  risk_created: 'Risk Detected',
  triage_complete: 'Triage Complete',
  simulation_running: 'Running Simulation',
  simulation_complete: 'Simulation Done',
  agents_deliberating: 'Agents Analyzing',
  mitigation_proposed: 'Mitigation Ready',
  approval_gate: 'Awaiting Approval',
  complete: 'Demo Complete',
};

export function DemoProgress() {
  const isRunning = useDemoStore((s) => s.isRunning);
  const currentStep = useDemoStore((s) => s.currentStep);
  const stepIndex = useDemoStore((s) => s.stepIndex);
  const totalSteps = useDemoStore((s) => s.totalSteps);

  if (!isRunning && currentStep !== 'complete') return null;

  const pct = totalSteps > 0 ? ((stepIndex + 1) / totalSteps) * 100 : 0;
  const label = currentStep ? STEP_LABELS[currentStep] || currentStep : '';

  return (
    <div className="demo-progress">
      <div className="demo-progress-bar">
        <div className="demo-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="demo-progress-label">
        <span className="demo-progress-step">
          Step {stepIndex + 1}/{totalSteps}
        </span>
        <span className="demo-progress-text">{label}</span>
      </div>
    </div>
  );
}
