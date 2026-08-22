import { createColumnHelper, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Table } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import { useDeleteUser, useReactivateUser, useSuspendUser } from "@/hooks/useUsers";
import type { AppUser } from "@/types";

const columnHelper = createColumnHelper<AppUser>();

export function UsersTable({ users }: { users: AppUser[] }) {
  const suspendUser = useSuspendUser();
  const reactivateUser = useReactivateUser();
  const deleteUser = useDeleteUser();
  const toast = useToast();
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);

  const columns = [
    columnHelper.accessor("email", { header: "Email" }),
    columnHelper.accessor("role", {
      header: "Role",
      cell: (info) => (info.getValue() === "admin" ? "Admin" : "Coach"),
    }),
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => (
        <Pill tone={info.getValue() === "active" ? "teal" : "amber"}>
          {info.getValue() === "active" ? "Active" : "Suspended"}
        </Pill>
      ),
    }),
    columnHelper.display({
      id: "actions",
      header: "Actions",
      cell: (info) => {
        const user = info.row.original;

        async function handleSuspendToggle() {
          try {
            if (user.status === "active") {
              await suspendUser.mutateAsync(user.id);
              toast.show(`${user.email} suspended`);
            } else {
              await reactivateUser.mutateAsync(user.id);
              toast.show(`${user.email} reactivated`);
            }
          } catch {
            toast.show("Action failed", "error");
          }
        }

        async function handleConfirmDelete() {
          try {
            await deleteUser.mutateAsync(user.id);
            toast.show(`${user.email} removed`);
          } catch {
            toast.show("Failed to remove user", "error");
          } finally {
            setConfirmingDeleteId(null);
          }
        }

        if (confirmingDeleteId === user.id) {
          return (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate">Delete {user.email}?</span>
              <Button variant="danger" onClick={handleConfirmDelete} isLoading={deleteUser.isPending}>
                Confirm
              </Button>
              <Button variant="secondary" onClick={() => setConfirmingDeleteId(null)}>
                Cancel
              </Button>
            </div>
          );
        }

        return (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={handleSuspendToggle}
              isLoading={suspendUser.isPending || reactivateUser.isPending}
            >
              {user.status === "active" ? "Suspend" : "Reactivate"}
            </Button>
            <Button variant="danger" onClick={() => setConfirmingDeleteId(user.id)}>
              Delete
            </Button>
          </div>
        );
      },
    }),
  ];

  const table = useReactTable({ data: users, columns, getCoreRowModel: getCoreRowModel() });

  return <Table table={table} />;
}
