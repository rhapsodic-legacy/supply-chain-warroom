import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { WarRoomShell } from './components/layout/WarRoomShell';
import { useEventStream } from './hooks/useEventStream';

function AppInner() {
  useEventStream();
  return <WarRoomShell />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}
