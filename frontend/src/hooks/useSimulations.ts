import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { Simulation, SimulationBrief } from '../types/api';

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
