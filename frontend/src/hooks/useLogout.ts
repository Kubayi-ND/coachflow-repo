import { useMutation, useQueryClient } from "@tanstack/react-query";

import { supabase } from "@/lib/supabaseClient";

/** Wraps supabase.auth.signOut() as a mutation, matching the write-action
 * hook convention (frontend/CLAUDE.md "API integration pattern"). No
 * onSuccess navigation is needed: useSession()'s onAuthStateChange
 * subscription flips isAuthenticated to false as soon as signOut()
 * resolves, and RequireAuth (src/app/router.tsx) redirects to /login
 * reactively. Throws on failure so callers can catch + toast.
 *
 * Clears the React Query cache on sign-out: query keys aren't per-user, so
 * without this the next person to sign in on the same browser would briefly
 * see the previous coach's clients, drafts and sessions. */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      queryClient.clear();
    },
  });
}
