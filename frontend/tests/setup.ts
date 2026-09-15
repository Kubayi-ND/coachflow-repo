import "@testing-library/jest-dom";

import { vi } from "vitest";

// supabaseClient.ts calls createClient(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)
// at module load, and @supabase/supabase-js throws "supabaseUrl is required" when
// the value is empty. CI has no VITE_* env (they're build-time secrets, not test
// inputs), so any test that transitively imports apiClient/supabaseClient would
// crash on import — even when it mocks apiClient, because vi.mock's importOriginal
// still evaluates the real module graph. Stub harmless dummy values here (setup
// files run before each test file's imports are evaluated) so the client
// constructs; tests never make real network calls (apiFetch is mocked).
vi.stubEnv("VITE_SUPABASE_URL", "https://test.supabase.co");
vi.stubEnv("VITE_SUPABASE_ANON_KEY", "test-anon-key");
vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
