import { useDemoStore } from '../../stores/demoStore';

export function DemoButton() {
  const isRunning = useDemoStore((s) => s.isRunning);
  const currentStep = useDemoStore((s) => s.currentStep);
  const startDemo = useDemoStore((s) => s.startDemo);
  const cancelDemo = useDemoStore((s) => s.cancelDemo);
  const clearDemo = useDemoStore((s) => s.clearDemo);

  if (currentStep === 'complete') {
    return (
      <button
        onClick={clearDemo}
        className="demo-btn demo-btn-reset"
      >
        <span className="demo-btn-icon">&#x21BB;</span>
        Reset Demo
      </button>
    );
  }

  if (isRunning) {
    return (
      <button
        onClick={cancelDemo}
        className="demo-btn demo-btn-cancel"
      >
        <span className="demo-btn-icon">&#x25A0;</span>
        Cancel Demo
      </button>
    );
  }

  return (
    <button
      onClick={startDemo}
      className="demo-btn demo-btn-start"
    >
      <span className="demo-btn-icon">&#x25B6;</span>
      Run Demo
    </button>
  );
}
