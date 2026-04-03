interface ErrorCardProps {
  message: string;
  className?: string;
  onRetry?: () => void;
}

export function ErrorCard({ message, className = '', onRetry }: ErrorCardProps) {
  return (
    <div
      className={`war-room-card glow-critical p-4 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
          style={{ background: 'var(--wr-red-dim)', color: 'var(--wr-red)' }}
        >
          !
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium" style={{ color: 'var(--wr-red)' }}>
            System Error
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--wr-text-secondary)' }}>
            {message}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 text-xs font-medium px-3 py-1 rounded"
              style={{
                background: 'var(--wr-red-dim)',
                color: 'var(--wr-red)',
                border: '1px solid rgba(248, 81, 73, 0.3)',
              }}
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
