import { expect, test } from "@playwright/test";

// Requires TEST_EMAIL / TEST_PASSWORD env vars for a seeded Supabase test
// user, and a backend running with fixture data. Skipped until that harness
// exists — see backend/CLAUDE.md testing notes for the fixture convention.
test.skip("coach can approve a pending draft", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env.TEST_EMAIL ?? "");
  await page.getByLabel("Password").fill(process.env.TEST_PASSWORD ?? "");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.goto("/approvals");
  const firstDraft = page.locator("textarea").first();
  await expect(firstDraft).toBeVisible();

  await page.getByRole("button", { name: "Approve & send" }).first().click();
  await expect(page.getByText("Sent")).toBeVisible();
});
