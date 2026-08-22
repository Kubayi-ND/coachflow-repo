import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/components/ui/Toast";
import { ImportPage } from "@/features/admin/ImportPage";
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

describe("ImportPage", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
    vi.mocked(apiFetch).mockResolvedValue([]);
  });

  it("won't start an import without a folder id", async () => {
    renderWithProviders(<ImportPage />);

    fireEvent.click((await screen.findAllByRole("button", { name: /start import/i }))[0]);

    expect(await screen.findByText(/paste a drive folder id/i)).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalledWith("/api/admin/imports", expect.anything());
  });

  it("starts a calendar import with the tenant, source, and folder id", async () => {
    renderWithProviders(<ImportPage />);

    const folderInputs = await screen.findAllByPlaceholderText("Drive folder id");
    fireEvent.change(folderInputs[0], { target: { value: "folder-123" } });
    fireEvent.click(screen.getAllByRole("button", { name: /start import/i })[0]);

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/admin/imports",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ tenant_id: "tenant_a", source: "calendar", folder_id: "folder-123" }),
        })
      )
    );
  });
});
