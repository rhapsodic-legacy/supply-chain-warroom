import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { AlertRuleBrief, AlertRule, AlertRuleCreate } from '../types/api';

export function useAlertRules() {
  return useQuery({
    queryKey: ['alert-rules'],
    queryFn: () =>
      api.get<AlertRuleBrief[]>('/api/v1/alert-rules').then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useAlertRuleDetail(ruleId: string | null) {
  return useQuery({
    queryKey: ['alert-rule-detail', ruleId],
    queryFn: () =>
      api.get<AlertRule>(`/api/v1/alert-rules/${ruleId}`).then((r) => r.data),
    enabled: !!ruleId,
    staleTime: 30_000,
  });
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AlertRuleCreate) =>
      api.post<AlertRule>('/api/v1/alert-rules', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-rules'] });
    },
  });
}

export function useToggleAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) =>
      api.post<AlertRule>(`/api/v1/alert-rules/${ruleId}/toggle`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-rules'] });
    },
  });
}

export function useDeleteAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) =>
      api.delete(`/api/v1/alert-rules/${ruleId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-rules'] });
    },
  });
}

export function useEvaluateRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post('/api/v1/alert-rules/evaluate').then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-rules'] });
    },
  });
}
