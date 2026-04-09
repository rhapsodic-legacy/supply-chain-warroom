import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import api from '../lib/api';
import type { AgentDecision, AgentDecisionBrief, ChatMessage, ChatRequest, ChatResponse } from '../types/api';

export function useDecisions(agentType?: string) {
  return useQuery({
    queryKey: ['agent-decisions', { agentType }],
    queryFn: () => {
      const params = agentType ? { agent_type: agentType } : {};
      return api
        .get<AgentDecisionBrief[]>('/api/v1/agents/decisions', { params })
        .then((r) => r.data);
    },
    refetchInterval: 10_000,
  });
}

export function useDecisionDetail(decisionId: string | null) {
  return useQuery({
    queryKey: ['agent-decision-detail', decisionId],
    queryFn: () =>
      api.get<AgentDecision>(`/api/v1/agents/decisions/${decisionId}`).then((r) => r.data),
    enabled: !!decisionId,
    staleTime: 30_000,
  });
}

export function useDecisionAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, notes }: { id: string; action: 'approve' | 'reject'; notes?: string }) =>
      api
        .patch<AgentDecision>(`/api/v1/agents/decisions/${id}`, { action, notes })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-decisions'] });
    },
  });
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const mutation = useMutation({
    mutationFn: (request: ChatRequest) =>
      api.post<ChatResponse>('/api/v1/agents/chat', request).then((r) => r.data),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          timestamp: data.timestamp || new Date().toISOString(),
        },
      ]);
    },
  });

  const sendMessage = useCallback(
    (content: string) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content, timestamp: new Date().toISOString() },
      ]);
      mutation.mutate({ message: content });
    },
    [mutation]
  );

  return {
    messages,
    sendMessage,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}
