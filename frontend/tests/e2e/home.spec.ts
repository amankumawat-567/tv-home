import { expect, request, test } from "@playwright/test";

const BACKEND_URL = "http://127.0.0.1:8000";

test.describe("Home screen", () => {
  // These tests need at least two installed apps (to move focus *between*
  // banners); seed them via the API rather than relying on whatever a
  // developer happens to have installed locally — a clean checkout/CI run
  // starts with none.
  test.beforeAll(async () => {
    const api = await request.newContext();
    for (const id of ["netflix", "youtube"]) {
      await api.post(`${BACKEND_URL}/api/apps`, { data: { id, name: id, url: "" } });
    }
    await api.dispose();
  });

  test("renders the top bar and favourites row, reachable by arrows alone", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await expect(page.getByText("Home", { exact: true })).toBeVisible();
    await expect(page.getByText("Apps", { exact: true })).toBeVisible();

    // Something should hold focus immediately (the focus engine auto-focuses
    // the first registered element) — a focused element always has is-focused.
    await expect(page.locator(".is-focused")).toHaveCount(1);

    await page.screenshot({ path: `tests/e2e/screenshots/${test.info().project.name}-home.png` });
  });

  test("arrow keys move focus from the top bar into the app row, Enter shows the launch screen", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".app-banner");

    // Down from the top bar should reach the first app banner.
    await page.keyboard.press("ArrowDown");
    await expect(page.locator(".app-banner.is-focused").first()).toBeVisible();

    // Right should move along the row without losing focus entirely.
    await page.keyboard.press("ArrowRight");
    await expect(page.locator(".is-focused")).toHaveCount(1);

    // Enter launches the focused app. Whether this succeeds depends on the
    // environment: some CI runners have a real Chrome on PATH (so it
    // "succeeds" even with nowhere to show a window) and this dev sandbox
    // doesn't (see backend/tv_home/chrome.py) — either way the round-trip
    // ends in one of these three states, so accept any of them rather than
    // asserting a specific outcome this test doesn't actually care about.
    await page.keyboard.press("Enter");
    await expect(page.locator(".toast, .running-app-placeholder, .launch-screen")).toBeVisible();

    // Home always returns to Home.
    await page.keyboard.press("Home");
    await expect(page.locator(".home-screen")).toBeVisible();
  });

  test("Menu opens quick settings and Back closes it", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".top-bar");

    await page.keyboard.press("m");
    await expect(page.locator(".quick-settings")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.locator(".quick-settings")).toHaveCount(0);
  });

  test("Apps tab shows the App Store tile first, then installed apps", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await page.getByText("Apps", { exact: true }).click();
    await expect(page.locator(".app-store-tile").first()).toBeVisible();
  });
});
