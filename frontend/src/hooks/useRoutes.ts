import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { ShippingRoute } from '../types/api';

export function useRoutes() {
  return useQuery({
    queryKey: ['routes'],
    queryFn: () =>
      api.get<ShippingRoute[]>('/api/v1/routes').then((r) => r.data),
    staleTime: 30_000,
  });
}

export function useRoute(id: string) {
  return useQuery({
    queryKey: ['routes', id],
    queryFn: () =>
      api.get<ShippingRoute>(`/api/v1/routes/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}
