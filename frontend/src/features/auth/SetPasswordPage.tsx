import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { supabase } from "@/lib/supabaseClient";

/** Serves both the account-setup (invite) and forgot-password (recovery)
 * flows — Supabase Auth resolves either link to the same kind of recovery
 * session client-side (supabaseClient.ts uses createClient() with default
 * options, so detectSessionInUrl is on). Once that session exists, setting
 * the password is just supabase.auth.updateUser — no backend route needed. */
export function SetPasswordPage() {
  const navigate = useNavigate();
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
    setSubmitting(false);

    if (updateError) {
      setError(updateError.message);
      return;
    }
    navigate("/", { replace: true });
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate/20 p-8">
        <h1 className="text-2xl">Set your password</h1>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="password">
            New password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-slate/30 px-3 py-2 bg-transparent"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="confirmPassword">
            Confirm password
          </label>
          <input
            id="confirmPassword"
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full rounded-md border border-slate/30 px-3 py-2 bg-transparent"
          />
        </div>
        {error && <p className="text-sm text-amber">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Saving..." : "Set password"}
        </Button>
      </form>
    </div>
  );
}
