import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { Supplier } from '../types/api';

export function useSuppliers() {
  return useQuery({
    queryKey: ['suppliers'],
    queryFn: () =>
      api.get<Supplier[]>('/api/v1/suppliers').then((r) => r.data),
    staleTime: 30_000,
  });
}

export function useSupplier(id: string) {
  return useQuery({
    queryKey: ['suppliers', id],
    queryFn: () =>
      api.get<Supplier>(`/api/v1/suppliers/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}
