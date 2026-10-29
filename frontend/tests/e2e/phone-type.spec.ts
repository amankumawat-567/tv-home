import { expect, request, test } from "@playwright/test";

const BACKEND_URL = "http://127.0.0.1:8000";

test.describe("Phone typing (I2)", () => {
  test.beforeAll(async () => {
    const api = await request.newContext();
    await api.post(`${BACKEND_URL}/api/first-run/complete`);
    await api.dispose();
  });

  test("scanning the QR and typing on \"the phone\" fills the field and advances the step", async ({ page }) => {
    let capturedToken: string | null = null;
    page.on("response", async (res) => {
      if (res.request().method() === "POST" && res.url().endsWith("/api/type/start")) {
        capturedToken = (await res.json().catch(() => null))?.token ?? null;
      }
    });

    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await page.getByText("Apps", { exact: true }).click();
    await page.getByText("App Store").click();
    await page.getByText("Add a website").click();
    await expect(page.locator(".keyboard-overlay")).toBeVisible();

    await page.getByLabel("Type on your phone").click();
    await expect(page.locator(".qr-code")).toBeVisible();
    await expect.poll(() => capturedToken).not.toBeNull();

    // Simulate the phone's own page posting keystrokes, then Done — exactly
    // what the served /type/<token> page's inline JS does (phone_type.py).
    await page.request.post(`${BACKEND_URL}/type/${capturedToken}`, { data: { value: "My Site" } });
    await expect(page.locator(".keyboard-value")).toHaveText("My Site");

    await page.request.post(`${BACKEND_URL}/type/${capturedToken}/done`);
    // Submitting the name step moves straight to the URL step, reusing the
    // same name — confirms the phone's "Done" actually drove onSubmit, not
    // just updated local state.
    await expect(page.locator(".keyboard-label")).toHaveText("Website for My Site");
  });
});
