import type { SelectHTMLAttributes } from "react";

export function Select({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`rounded-md border border-slate/30 bg-transparent px-2 py-1.5 text-sm ${className}`}
      {...props}
    />
  );
}
