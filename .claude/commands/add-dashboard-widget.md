---
description: Scaffold a new dashboard widget component with hook, types, and test.
argument-hint: <WidgetName> [--data-source /api/v1/endpoint]
---

Scaffold a new React dashboard widget following project conventions.

$ARGUMENTS contains:
- WidgetName: PascalCase component name (e.g., SupplierRiskHeatmap)
- --data-source: API endpoint path (optional)

## Steps

1. Read frontend/CLAUDE.md for component and hook patterns
2. Check frontend/src/components/panels/ for existing widgets to follow the pattern
3. Create `frontend/src/components/panels/<WidgetName>.tsx`:
   - Props interface with className
   - Three-state rendering (loading, error, empty, success)
   - Uses a custom hook for data fetching
   - Wrapped in Card component with dark theme styling
4. Create `frontend/src/hooks/use<WidgetName>.ts`:
   - TanStack Query hook calling the data source endpoint
   - Typed response matching backend schema
5. Add any needed TypeScript types to `frontend/src/types/api.ts`
6. Add the widget to the dashboard grid in the appropriate page
7. Print summary of created files
