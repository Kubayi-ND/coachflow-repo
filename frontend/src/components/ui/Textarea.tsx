import { forwardRef, type TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className = "", error = false, ...props },
  ref
) {
  return (
    <textarea
      ref={ref}
      aria-invalid={error || undefined}
      className={`w-full rounded-md border bg-transparent px-3 py-2 text-sm transition-colors placeholder:text-slate/60 focus:outline-none focus:ring-2 focus:ring-teal/30 ${
        error ? "border-amber focus:border-amber" : "border-slate/30 focus:border-teal"
      } ${className}`}
      {...props}
    />
  );
});
