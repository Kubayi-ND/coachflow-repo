import { useState } from "react";

import { CopyIcon } from "./icons";

/** Copies text to the clipboard with a short "Copied" confirmation. Icon-only
 * by default (pass `label` to show text), always with an accessible name. */
export function CopyButton({ text, label, ariaLabel = "Copy" }: { text: string; label?: string; ariaLabel?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be unavailable (insecure context, denied permission); nothing to undo.
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={label ? undefined : ariaLabel}
      className="inline-flex flex-shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-xs text-slate transition-colors hover:bg-surface-2 hover:text-ink"
    >
      <CopyIcon className="h-3.5 w-3.5" />
      {copied ? "Copied" : label}
    </button>
  );
}
