import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type {
  ExecutiveSummary,
  Simulation,
  SimulationBrief,
  SimulationCompareResponse,
} from '../types/api';

export function useSimulations() {
  return useQuery({
    queryKey: ['simulations'],
    queryFn: () =>
      api.get<SimulationBrief[]>('/api/v1/simulations').then((r) => r.data),
  });
}

export function useSimulation(id: string) {
  return useQuery({
    queryKey: ['simulations', id],
    queryFn: () =>
      api.get<Simulation>(`/api/v1/simulations/${id}`).then((r) => r.data),
    enabled: !!id,
    refetchInterval: (query) => {
      const sim = query.state.data;
      return sim?.status === 'running' ? 2_000 : false;
    },
  });
}

interface RunSimulationParams {
  name: string;
  description?: string;
  scenario_params: Record<string, unknown>;
  iterations?: number;
}

export function useExecutiveSummary(simId: string | null) {
  return useQuery({
    queryKey: ['executive-summary', simId],
    queryFn: () =>
      api.get<ExecutiveSummary>(`/api/v1/simulations/${simId}/executive-summary`).then((r) => r.data),
    enabled: !!simId,
    staleTime: 5 * 60_000,
  });
}

export function useCompareSimulations(simulationIds: string[]) {
  return useQuery({
    queryKey: ['simulations', 'compare', simulationIds],
    queryFn: () =>
      api
        .post<SimulationCompareResponse>('/api/v1/simulations/compare', {
          simulation_ids: simulationIds,
        })
        .then((r) => r.data),
    enabled: simulationIds.length >= 2,
    staleTime: 60_000,
  });
}

export function useRunSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: RunSimulationParams) =>
      api.post<Simulation>('/api/v1/simulations', params).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['simulations'] });
    },
  });
}
