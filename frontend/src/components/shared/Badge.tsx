interface BadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  children: React.ReactNode;
  dot?: boolean;
}

export function Badge({ severity, children, dot }: BadgeProps) {
  return (
    <span className={`badge badge-${severity}`}>
      {dot && (
        <span
          className="inline-block w-1.5 h-1.5 rounded-full pulse-dot"
          style={{
            backgroundColor:
              severity === 'critical'
                ? 'var(--wr-red)'
                : severity === 'high'
                  ? '#db6d28'
                  : severity === 'medium'
                    ? 'var(--wr-amber)'
                    : severity === 'low'
                      ? 'var(--wr-green)'
                      : 'var(--wr-cyan)',
          }}
        />
      )}
      {children}
    </span>
  );
}
