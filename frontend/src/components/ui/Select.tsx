import { forwardRef, type SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className = "", error = false, ...props },
  ref
) {
  return (
    <select
      ref={ref}
      aria-invalid={error || undefined}
      className={`rounded-lg border bg-surface-2 px-2.5 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:ring-2 focus:ring-teal/20 ${
        error ? "border-amber focus:border-amber" : "border-border focus:border-teal"
      } ${className}`}
      {...props}
    />
  );
});
