# Frontend — Supply Chain War Room Dashboard

React 18 + TypeScript + Vite + Tailwind CSS + Shadcn/ui. Dark-themed command center.

## Structure

```
frontend/src/
  components/
    layout/          WarRoomShell, Sidebar, StatusBar
    panels/          Dashboard widgets (GlobalMap, RiskFeed, SupplierGrid, etc.)
    shared/          Button, Card, Badge, Modal, LoadingSpinner
  hooks/             React Query data hooks
  stores/            Zustand stores (dashboard, simulation)
  types/             TypeScript interfaces (derived from backend schemas)
  styles/            war-room.css (dark theme, glows, animations)
```

## Widget Pattern

Every dashboard panel follows this structure:
```tsx
export function WidgetName({ className }: { className?: string }) {
  const { data, isLoading, error } = useRelevantHook();
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorCard message={error.message} />;
  if (!data?.length) return <EmptyState message="No data available" />;
  return <Card className={className}>...</Card>;
}
```
- Always handle loading, error, and empty states
- Accept className for layout flexibility
- Data fetching in hooks, not components

## Hook Pattern

All data hooks use TanStack Query:
```tsx
export function useSuppliers() {
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/api/v1/suppliers").then(r => r.data),
    staleTime: 30_000,
  });
}
```

## Styling

- Tailwind utility classes only (no CSS modules)
- Dark theme: background #0a0e14, accents: red/green/amber/cyan
- Monospace for numbers and IDs
- Glow effects on critical risk events
- Consistent spacing: p-4 cards, gap-4 grids

## Running

```bash
npm run dev          # Vite dev server on 5173
npm test             # Vitest watch mode
npm run build        # Production build
```
