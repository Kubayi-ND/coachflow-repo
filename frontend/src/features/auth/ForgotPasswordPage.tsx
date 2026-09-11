import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/apiClient";

/** POST /api/auth/forgot-password always returns 204 whether or not the
 * email is registered (avoids leaking an enumeration signal) — this page
 * shows the same generic message regardless of the outcome, so the UI
 * doesn't undo what the backend just took care to hide. */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await apiFetch("/api/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
    } catch {
      // Intentionally ignored — see the module doc comment above.
    }
    setSubmitting(false);
    setSubmitted(true);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-surface p-8 shadow-cardmd">
        <h1 className="font-display text-2xl text-ink">Reset your password</h1>

        {submitted ? (
          <p className="text-sm text-slate">
            If that email has an account, we&apos;ve sent a link to reset your password.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm text-slate" htmlFor="email">
                Email
              </label>
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <Button type="submit" isLoading={submitting} className="w-full">
              Send reset link
            </Button>
          </form>
        )}

        <Link to="/login" className="block text-xs text-teal hover:underline">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
