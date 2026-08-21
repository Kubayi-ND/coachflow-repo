import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { Client } from "@/types";

export function useClients() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: () => apiFetch<Client[]>("/api/clients"),
  });
}
