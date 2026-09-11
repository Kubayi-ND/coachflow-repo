import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { SESSION_TYPE_IDS, SESSION_TYPES } from "@/types";

const clientFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required."),
  email: z.string().trim().email("Enter a valid email address."),
  tenantId: z.enum(["tenant_a", "tenant_b"]),
  sessionTypes: z.array(z.string()).default([]),
  context: z.string().trim().optional(),
});
export type ClientFormValues = z.infer<typeof clientFormSchema>;

/** Shared by create (ClientsDirectory) and edit (ClientDetail) — same field
 * set except `context`, which only the create flow shows: it seeds a
 * Context Library entry at creation time, edits to a client's context go
 * through the existing Context Library editor instead. */
export function ClientForm({
  defaultValues,
  submitLabel,
  showContext = false,
  isPending = false,
  onSubmit,
  onCancel,
}: {
  defaultValues?: Partial<ClientFormValues>;
  submitLabel: string;
  showContext?: boolean;
  isPending?: boolean;
  onSubmit: (values: ClientFormValues) => void;
  onCancel?: () => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClientFormValues>({
    resolver: zodResolver(clientFormSchema),
    defaultValues: { tenantId: "tenant_a", sessionTypes: [], ...defaultValues },
  });

  const submit = handleSubmit(onSubmit);

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-[200px] flex-1">
          <Input placeholder="Client name" error={!!errors.name} {...register("name")} />
          {errors.name && <p className="mt-1 text-xs text-amber">{errors.name.message}</p>}
        </div>
        <div className="min-w-[220px] flex-1">
          <Input type="email" placeholder="name@example.com" error={!!errors.email} {...register("email")} />
          {errors.email && <p className="mt-1 text-xs text-amber">{errors.email.message}</p>}
        </div>
        <Select {...register("tenantId")}>
          <option value="tenant_a">Tenant A</option>
          <option value="tenant_b">Tenant B</option>
        </Select>
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium text-slate">Session types</p>
        <div className="flex flex-wrap gap-3">
          {SESSION_TYPE_IDS.map((id) => (
            <label key={id} className="flex items-center gap-1.5 text-sm text-ink">
              <input type="checkbox" value={id} className="rounded border-border" {...register("sessionTypes")} />
              {SESSION_TYPES[id].label}
            </label>
          ))}
        </div>
      </div>

      {showContext && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate">Context (optional)</p>
          <Textarea
            rows={3}
            placeholder="Anything the AI should know when preparing drafts for this client — goals, working style, prior history…"
            {...register("context")}
          />
        </div>
      )}

      <div className="flex items-center gap-2">
        <Button type="submit" isLoading={isPending}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
