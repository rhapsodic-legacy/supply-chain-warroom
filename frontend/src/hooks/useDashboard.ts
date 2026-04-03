import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { DashboardOverview, SupplyHealthItem } from '../types/api';

export function useOverview() {
  return useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: () =>
      api.get<DashboardOverview>('/api/v1/dashboard/').then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useSupplyHealth() {
  return useQuery({
    queryKey: ['dashboard', 'supply-health'],
    queryFn: () =>
      api.get<SupplyHealthItem[]>('/api/v1/dashboard/supply-health').then((r) => r.data),
    refetchInterval: 30_000,
  });
}
