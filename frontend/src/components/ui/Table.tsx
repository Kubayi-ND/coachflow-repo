import { flexRender, type Table as TanstackTable } from "@tanstack/react-table";

/** Thin wrapper around TanStack Table's headless API — used by client lists
 * and session history tables. Wrapped in the shared card shell so a bare
 * `<Table>` matches every other data surface; pass `bare` to opt out when
 * the caller already provides its own card (e.g. inside another card). */
export function Table<T>({ table, bare = false }: { table: TanstackTable<T>; bare?: boolean }) {
  const content = (
    <table className="w-full text-left text-sm">
      <thead className="bg-surface-2">
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <th key={header.id} className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate">
                {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody className="divide-y divide-border">
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id} className="hover:bg-surface-2/60 transition-colors">
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="px-4 py-3 tabular-nums">
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );

  if (bare) return content;

  return <div className="overflow-hidden overflow-x-auto rounded-xl border border-border bg-surface shadow-card">{content}</div>;
}
