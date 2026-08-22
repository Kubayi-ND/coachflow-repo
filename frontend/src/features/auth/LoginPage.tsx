import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useSession } from "@/hooks/useSession";
import { supabase } from "@/lib/supabaseClient";

export function LoginPage() {
  const { isAuthenticated } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    setSubmitting(false);
    if (signInError) setError(signInError.message);
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate/20 p-8">
        <h1 className="text-2xl">CoachFlow</h1>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border border-slate/30 px-3 py-2 bg-transparent"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-slate" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-slate/30 px-3 py-2 bg-transparent"
          />
        </div>
        <Link to="/forgot-password" className="block text-xs text-teal hover:underline">
          Forgot password?
        </Link>
        {error && <p className="text-sm text-amber">{error}</p>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
