import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { apiFetch } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/apiClient")>();
  return { ...actual, apiFetch: vi.fn() };
});

/** The backend always returns 204 from /api/auth/forgot-password regardless
 * of whether the email is registered, to avoid an enumeration side channel.
 * This page must show the same generic message either way. */
describe("ForgotPasswordPage", () => {
  it("shows the generic success message when the request succeeds", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(undefined);
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "real@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText(/we've sent a link/i)).toBeInTheDocument();
  });

  it("shows the same generic success message even when the request fails", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("network error"));
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "unknown@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText(/we've sent a link/i)).toBeInTheDocument();
  });
});
