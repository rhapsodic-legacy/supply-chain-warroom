import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { RiskEvent } from '../types/api';

export function useRiskEvents(activeOnly?: boolean) {
  return useQuery({
    queryKey: ['risk-events', { activeOnly }],
    queryFn: () => {
      const params = activeOnly ? { active_only: true } : {};
      return api.get<RiskEvent[]>('/api/v1/risks', { params }).then((r) => r.data);
    },
    refetchInterval: 10_000,
  });
}

export function useRiskEvent(id: string) {
  return useQuery({
    queryKey: ['risk-events', id],
    queryFn: () =>
      api.get<RiskEvent>(`/api/v1/risks/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}
