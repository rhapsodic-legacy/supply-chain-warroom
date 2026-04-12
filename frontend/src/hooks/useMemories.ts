import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { AgentMemoryBrief, AgentMemory, AgentMemoryStats } from '../types/api';

export function useMemories(agentType?: string, category?: string) {
  return useQuery({
    queryKey: ['agent-memories', { agentType, category }],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (agentType) params.agent_type = agentType;
      if (category) params.category = category;
      return api
        .get<AgentMemoryBrief[]>('/api/v1/agents/memories', { params })
        .then((r) => r.data);
    },
    refetchInterval: 30_000,
  });
}

export function useMemoryDetail(memoryId: string | null) {
  return useQuery({
    queryKey: ['agent-memory-detail', memoryId],
    queryFn: () =>
      api.get<AgentMemory>(`/api/v1/agents/memories/${memoryId}`).then((r) => r.data),
    enabled: !!memoryId,
    staleTime: 60_000,
  });
}

export function useMemoryStats() {
  return useQuery({
    queryKey: ['agent-memory-stats'],
    queryFn: () =>
      api.get<AgentMemoryStats>('/api/v1/agents/memories/stats').then((r) => r.data),
    refetchInterval: 30_000,
  });
}
