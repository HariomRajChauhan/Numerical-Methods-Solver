interface LoadingSkeletonProps {
  lines?: number;
  className?: string;
}

/** Pulse placeholders shown while data loads (no layout shift). */
export function LoadingSkeleton({ lines = 3, className = "" }: LoadingSkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className={`skeleton-shimmer h-3.5 rounded-lg bg-slate-200/80 dark:bg-white/[0.07] ${
            index === lines - 1 ? "w-2/3" : "w-full"
          }`}
        />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
