import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { DemandSignal, DemandSummary } from '../types/api';

export function useDemand(productId?: string) {
  return useQuery({
    queryKey: ['demand', { productId }],
    queryFn: () => {
      const params = productId ? { product_id: productId } : {};
      return api.get<DemandSignal[]>('/api/v1/demand', { params }).then((r) => r.data);
    },
    staleTime: 60_000,
  });
}

export function useDemandSummary() {
  return useQuery({
    queryKey: ['demand', 'summary'],
    queryFn: () =>
      api.get<DemandSummary[]>('/api/v1/demand/summary').then((r) => r.data),
    staleTime: 30_000,
  });
}
