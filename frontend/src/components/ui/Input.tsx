import { forwardRef, type InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className = "", error = false, ...props },
  ref
) {
  return (
    <input
      ref={ref}
      aria-invalid={error || undefined}
      className={`w-full rounded-lg border bg-surface-2 px-3 py-2 text-sm text-ink transition-colors placeholder:text-slate/60 focus:outline-none focus:ring-2 focus:ring-teal/20 ${
        error ? "border-amber focus:border-amber" : "border-border focus:border-teal"
      } ${className}`}
      {...props}
    />
  );
});
