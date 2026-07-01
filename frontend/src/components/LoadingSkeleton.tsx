interface LoadingSkeletonProps {
  lines?: number;
  className?: string;
}

export default function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={['space-y-3', className].join(' ')} aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className="skeleton-shimmer h-3 rounded-full border border-[var(--app-border)] bg-[var(--app-surface-muted)]"
          style={{ width: `${Math.max(44, 100 - index * 18)}%` }}
        />
      ))}
    </div>
  );
}
