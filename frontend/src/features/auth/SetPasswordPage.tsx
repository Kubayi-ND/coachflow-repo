import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/apiClient";
import { supabase } from "@/lib/supabaseClient";

/** Serves three flows: the forgot-password recovery link, and both a
 * temp-password admin-created account's forced first-login reset and a
 * voluntary later password change — all three land here with an existing
 * Supabase session (a recovery-link session, or a normal signed-in one), so
 * setting the password is just supabase.auth.updateUser. The forced-reset
 * case additionally needs the backend told, since must_reset_password lives
 * in our `users` table, not in anything Supabase Auth exposes. */
export function SetPasswordPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setSubmitting(false);
      setError(updateError.message);
      return;
    }

    try {
      await apiFetch("/api/auth/complete-password-reset", { method: "POST" });
    } catch {
      // Password is already changed in Supabase Auth either way; a failure
      // here just means a stale mustResetPassword flag, not a blocked login.
    }
    await queryClient.invalidateQueries({ queryKey: ["current-user"] });

    setSubmitting(false);
    navigate("/", { replace: true });
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-surface p-8 shadow-cardmd">
        <h1 className="font-display text-2xl text-ink">Set your password</h1>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="password">
            New password
          </label>
          <Input
            id="password"
            type="password"
            required
            minLength={8}
            error={!!error}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="confirmPassword">
            Confirm password
          </label>
          <Input
            id="confirmPassword"
            type="password"
            required
            minLength={8}
            error={!!error}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-amber">{error}</p>}
        <Button type="submit" isLoading={submitting} className="w-full">
          Set password
        </Button>
      </form>
    </div>
  );
}
