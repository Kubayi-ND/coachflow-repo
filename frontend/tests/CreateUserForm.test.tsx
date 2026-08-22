import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/components/ui/Toast";
import { CreateUserForm } from "@/features/admin/CreateUserForm";
import { apiFetch } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return { ...actual, apiFetch: vi.fn() };
});

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>
  );
}

describe("CreateUserForm", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("blocks submission with an invalid email", async () => {
    renderWithProviders(<CreateUserForm onDone={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("name@example.com"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: /create user/i }));

    expect(await screen.findByText(/valid email address/i)).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("submits the right payload and calls onDone with the generated credentials", async () => {
    const result = {
      user: {
        id: "1",
        email: "new@example.com",
        role: "admin",
        status: "active",
        mustResetPassword: true,
        assignedClientIds: [],
      },
      temporaryPassword: "generated-temp-password",
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(result);
    const onDone = vi.fn();
    renderWithProviders(<CreateUserForm onDone={onDone} />);

    fireEvent.change(screen.getByPlaceholderText("name@example.com"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "admin" } });
    fireEvent.click(screen.getByRole("button", { name: /create user/i }));

    await waitFor(() => expect(onDone).toHaveBeenCalledWith(result));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/admin/users",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ email: "new@example.com", role: "admin" }) })
    );
  });
});
