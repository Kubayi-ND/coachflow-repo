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
      className={`w-full rounded-lg border bg-surface-2 px-3 py-2 text-sm text-ink transition-colors placeholder:text-slate/60 focus:outline-none focus:ring-2 focus:ring-teal/20 ${
        error ? "border-amber focus:border-amber" : "border-border focus:border-teal"
      } ${className}`}
      {...props}
    />
  );
});
