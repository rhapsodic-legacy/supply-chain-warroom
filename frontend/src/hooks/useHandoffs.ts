import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { AgentHandoffSession } from '../types/api';

export function useHandoffSessions(limit = 20) {
  return useQuery({
    queryKey: ['agent-handoff-sessions', { limit }],
    queryFn: () =>
      api
        .get<AgentHandoffSession[]>('/api/v1/agents/handoffs/sessions', { params: { limit } })
        .then((r) => r.data),
    refetchInterval: 10_000,
  });
}
