import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-md border border-slate/30 bg-transparent px-3 py-2 text-sm ${className}`}
      {...props}
    />
  );
}
