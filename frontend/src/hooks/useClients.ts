import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/apiClient";
import type { Client, ClientCreateInput, ClientUpdateInput } from "@/types";

const CLIENTS_KEY = ["clients"] as const;

export function useClients() {
  return useQuery({
    queryKey: CLIENTS_KEY,
    queryFn: () => apiFetch<Client[]>("/api/clients"),
  });
}

export function useCreateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ClientCreateInput) =>
      apiFetch<Client>("/api/clients", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

export function useUpdateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ clientId, input }: { clientId: string; input: ClientUpdateInput }) =>
      apiFetch<Client>(`/api/clients/${clientId}`, { method: "PUT", body: JSON.stringify(input) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}

export function useDeleteClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (clientId: string) => apiFetch<void>(`/api/clients/${clientId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLIENTS_KEY }),
  });
}
