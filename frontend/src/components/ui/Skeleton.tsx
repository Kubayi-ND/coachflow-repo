/** Pulsing placeholder block, sized via className. Each view composes these
 * into its own layout so the skeleton matches the real content shape rather
 * than a generic spinner (frontend/CLAUDE.md: this is an operations
 * dashboard, not a report). */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate/15 ${className}`} />;
}
