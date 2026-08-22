import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useCreateUser } from "@/hooks/useUsers";
import { ApiError } from "@/lib/apiClient";
import type { CreateUserResult } from "@/types";

const createUserSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  role: z.enum(["admin", "general"]),
});
type CreateUserFormValues = z.infer<typeof createUserSchema>;

/** Creates the account directly with a generated one-time password (Supabase
 * email delivery isn't configured for this project, so an invite-link flow
 * silently fails after already creating the Auth account). The password is
 * returned exactly once — the caller is responsible for showing it to the
 * admin so it can be handed to the coach; the account is forced to reset it
 * on first login. */
export function CreateUserForm({ onDone }: { onDone: (result: CreateUserResult) => void }) {
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
      onSuccess: (result) => {
        reset();
        onDone(result);
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
        <Input type="email" placeholder="name@example.com" error={!!errors.email} {...register("email")} />
        {errors.email && <p className="mt-1 text-xs text-amber">{errors.email.message}</p>}
      </div>
      <Select {...register("role")}>
        <option value="general">Coach</option>
        <option value="admin">Admin</option>
      </Select>
      <Button type="submit" isLoading={createUser.isPending}>
        Create user
      </Button>
    </form>
  );
}
