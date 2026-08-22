import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useCreateUser } from "@/hooks/useUsers";
import { ApiError } from "@/lib/apiClient";

const createUserSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  role: z.enum(["admin", "general"]),
});
type CreateUserFormValues = z.infer<typeof createUserSchema>;

/** New user gets a Supabase-sent account-setup email (invite_user_by_email
 * on the backend) — there is no password field here, the user sets their
 * own via the link. */
export function CreateUserForm({ onDone }: { onDone: () => void }) {
  const createUser = useCreateUser();
  const toast = useToast();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateUserFormValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: "general" },
  });

  const onSubmit = handleSubmit((values) => {
    createUser.mutate(values, {
      onSuccess: () => {
        toast.show(`Invite sent to ${values.email}`);
        reset();
        onDone();
      },
      onError: (error) => {
        const message = error instanceof ApiError && error.status === 409 ? "A user with this email already exists." : "Failed to create user.";
        toast.show(message, "error");
      },
    });
  });

  return (
    <form onSubmit={onSubmit} noValidate className="mt-3 flex flex-wrap items-start gap-3 border-t border-slate/10 pt-3">
      <div className="min-w-[220px] flex-1">
        <Input type="email" placeholder="name@example.com" {...register("email")} />
        {errors.email && <p className="mt-1 text-xs text-amber">{errors.email.message}</p>}
      </div>
      <Select {...register("role")}>
        <option value="general">Coach</option>
        <option value="admin">Admin</option>
      </Select>
      <Button type="submit" disabled={createUser.isPending}>
        {createUser.isPending ? "Sending invite..." : "Send invite"}
      </Button>
    </form>
  );
}
