interface LoadingSpinnerProps {
  className?: string;
  label?: string;
}

export function LoadingSpinner({ className = '', label = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-8 ${className}`}>
      <div className="spinner" />
      <span className="text-xs uppercase tracking-widest" style={{ color: 'var(--wr-text-muted)' }}>
        {label}
      </span>
    </div>
  );
}
