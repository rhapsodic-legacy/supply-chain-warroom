interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  badge?: React.ReactNode;
  glow?: 'critical' | 'warning' | 'safe';
  noPadding?: boolean;
}

export function Card({ children, className = '', title, badge, glow, noPadding }: CardProps) {
  const glowClass = glow ? `glow-${glow}` : '';
  const paddingClass = noPadding ? '' : 'p-4';

  return (
    <div className={`war-room-card flex flex-col ${glowClass} ${paddingClass} ${className}`}>
      {(title || badge) && (
        <div className="flex items-center justify-between mb-3 flex-shrink-0">
          {title && (
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: 'var(--wr-text-secondary)' }}>
              {title}
            </h3>
          )}
          {badge}
        </div>
      )}
      {children}
    </div>
  );
}
