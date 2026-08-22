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
      className={`rounded-md border bg-transparent px-2 py-1.5 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-teal/30 ${
        error ? "border-amber focus:border-amber" : "border-slate/30 focus:border-teal"
      } ${className}`}
      {...props}
    />
  );
});
