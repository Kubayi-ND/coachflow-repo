import { flexRender, type Table as TanstackTable } from "@tanstack/react-table";

/** Thin wrapper around TanStack Table's headless API — used by client lists
 * and session history tables. */
export function Table<T>({ table }: { table: TanstackTable<T> }) {
  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate/20 text-slate">
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <th key={header.id} className="px-3 py-2 font-medium">
                {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id} className="border-b border-slate/10 last:border-0">
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="px-3 py-2 tabular-nums">
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
