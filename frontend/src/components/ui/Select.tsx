import { forwardRef, type SelectHTMLAttributes } from "react";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className = "", ...props },
  ref
) {
  return (
    <select
      ref={ref}
      className={`rounded-md border border-slate/30 bg-transparent px-2 py-1.5 text-sm ${className}`}
      {...props}
    />
  );
});
