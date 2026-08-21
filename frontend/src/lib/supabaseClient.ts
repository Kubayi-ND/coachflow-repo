import { createClient } from "@supabase/supabase-js";

// Auth-only client — login, session refresh, JWT retrieval. It never queries
// Supabase tables directly; all app data reads/writes go through apiClient.ts
// so authorization logic lives in one place (the backend). See
// frontend/CLAUDE.md "What NOT to build here".
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
