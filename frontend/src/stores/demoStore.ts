import { create } from 'zustand';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || '';

export interface DemoState {
  isRunning: boolean;
  currentStep: string | null;
  stepIndex: number;
  totalSteps: number;
  highlightedPanel: string | null;
  agentTier: string | null;
  simulationId: string | null;
  error: boolean;

  startDemo: () => Promise<void>;
  cancelDemo: () => Promise<void>;
  setStep: (step: string, panel: string | null, stepIndex: number, totalSteps: number, extra?: Record<string, unknown>) => void;
  clearDemo: () => void;
}

export const useDemoStore = create<DemoState>((set) => ({
  isRunning: false,
  currentStep: null,
  stepIndex: 0,
  totalSteps: 9,
  highlightedPanel: null,
  agentTier: null,
  simulationId: null,
  error: false,

  startDemo: async () => {
    set({ isRunning: true, currentStep: null, stepIndex: 0, highlightedPanel: null, agentTier: null, simulationId: null, error: false });
    try {
      await axios.post(`${API}/api/v1/demo/run`);
    } catch {
      set({ isRunning: false, error: true });
    }
  },

  cancelDemo: async () => {
    try {
      await axios.post(`${API}/api/v1/demo/cancel`);
    } catch {
      // ignore
    }
    set({ isRunning: false, currentStep: null, highlightedPanel: null });
  },

  setStep: (step, panel, stepIndex, totalSteps, extra) => {
    const agentTier = (extra?.agent_tier as string) || undefined;
    const simId = (extra?.simulation_id as string) || undefined;
    if (step === 'complete') {
      set((s) => ({
        currentStep: 'complete',
        stepIndex: totalSteps - 1,
        totalSteps,
        highlightedPanel: null,
        isRunning: false,
        error: extra?.error === true,
        simulationId: simId ?? s.simulationId,
      }));
    } else {
      set((s) => ({
        currentStep: step,
        stepIndex,
        totalSteps,
        highlightedPanel: panel,
        isRunning: true,
        agentTier: agentTier ?? s.agentTier,
        simulationId: simId ?? s.simulationId,
      }));
    }
  },

  clearDemo: () =>
    set({
      isRunning: false,
      currentStep: null,
      stepIndex: 0,
      highlightedPanel: null,
      agentTier: null,
      simulationId: null,
      error: false,
    }),
}));
