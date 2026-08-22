import type { TextareaHTMLAttributes } from "react";

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-md border border-slate/30 bg-transparent px-3 py-2 text-sm ${className}`}
      {...props}
    />
  );
}
