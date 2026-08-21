import { useMutation } from "@tanstack/react-query";

import { supabase } from "@/lib/supabaseClient";

/** Wraps supabase.auth.signOut() as a mutation, matching the write-action
 * hook convention (frontend/CLAUDE.md "API integration pattern"). No
 * onSuccess navigation is needed: useSession()'s onAuthStateChange
 * subscription flips isAuthenticated to false as soon as signOut()
 * resolves, and RequireAuth (src/app/router.tsx) redirects to /login
 * reactively. Throws on failure so callers can catch + toast. */
export function useLogout() {
  return useMutation({
    mutationFn: async () => {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    },
  });
}
