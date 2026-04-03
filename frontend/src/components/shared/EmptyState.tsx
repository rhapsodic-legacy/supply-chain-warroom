interface EmptyStateProps {
  message?: string;
  className?: string;
  icon?: string;
}

export function EmptyState({ message = 'No data available', className = '', icon = '---' }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 py-8 ${className}`}>
      <span className="font-mono-numbers text-2xl" style={{ color: 'var(--wr-text-muted)' }}>
        {icon}
      </span>
      <span className="text-xs uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
        {message}
      </span>
    </div>
  );
}
