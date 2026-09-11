import type { ReactNode } from "react";

/** Readable renderer for untyped AI-generated JSON (scorecards, citations —
 * structured_critique is stored as Postgres jsonb with no fixed schema, so
 * this stays generic rather than assuming field names that may not match
 * what the model actually returns for a given prompt template. */
export function JsonTree({ value }: { value: unknown }) {
  return <div className="text-sm leading-6">{renderValue(value)}</div>;
}

function renderValue(value: unknown): ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-slate/60">—</span>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-slate/60">—</span>;
    return (
      <ul className="space-y-2">
        {value.map((item, i) => (
          <li key={i} className="rounded-lg border border-border px-3 py-2">
            {renderValue(item)}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-slate/60">—</span>;
    return (
      <dl className="space-y-2">
        {entries.map(([key, val]) => (
          <div key={key}>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate">{humanizeKey(key)}</dt>
            <dd className="mt-0.5">{renderValue(val)}</dd>
          </div>
        ))}
      </dl>
    );
  }
  if (typeof value === "number") {
    return <span className="tabular-nums">{value}</span>;
  }
  if (typeof value === "boolean") {
    return <span className={value ? "text-teal" : "text-slate"}>{value ? "Yes" : "No"}</span>;
  }
  return <span className="whitespace-pre-wrap">{String(value)}</span>;
}

function humanizeKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
