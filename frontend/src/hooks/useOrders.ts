import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { OrderBrief } from '../types/api';

export function useOrders(status?: string) {
  return useQuery({
    queryKey: ['orders', { status }],
    queryFn: () => {
      const params = status ? { status } : {};
      return api.get<OrderBrief[]>('/api/v1/orders', { params }).then((r) => r.data);
    },
    staleTime: 15_000,
  });
}

interface OrderStats {
  [status: string]: number;
}

export function useOrderStats() {
  return useQuery({
    queryKey: ['orders', 'stats'],
    queryFn: () =>
      api.get<OrderStats>('/api/v1/orders/stats').then((r) => r.data),
    staleTime: 30_000,
  });
}
