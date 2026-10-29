import { expect, test } from "@playwright/test";

// This backend is shared across every spec file and viewport project in this
// suite (see playwright.config.ts) and firstRunComplete persists to
// settings.json, with no reset endpoint — so there is exactly one
// opportunity across the whole run to see the wizard in its initial state.
// In CI (a fresh container each run) it genuinely shows and this test
// exercises the full flow for real; on a repeated local run it may already
// be complete from an earlier pass, in which case this skips rather than
// reporting a false failure. (Keep this file to a single test for exactly
// that reason — a second one would always skip once the first has run.)
//
// Step transitions are driven by clicking the footer buttons rather than
// relying on arrow-key focus landing exactly where expected after a step
// remounts — that's deliberately tested elsewhere (home.spec.ts); this test
// is about the wizard's own step logic, so Back and the Home-key skip (the
// two behaviors unique to this screen) are the only places it drives via
// the keyboard.
test("first-run wizard walks Wi-Fi, remote, apps, then Home — Home key skips the rest", async ({ page }) => {
  await page.goto("/");
  // Wait for the app to settle into whichever state it's actually going to
  // show — .isVisible() alone is a one-shot check with no retry, so without
  // this it almost always reads false (and skips every run) simply because
  // the initial /api/state fetch hasn't resolved yet.
  await page.waitForSelector(".first-run, .top-bar", { timeout: 10000 });
  const wizardVisible = await page.locator(".first-run").isVisible();
  test.skip(!wizardVisible, "first-run was already completed by an earlier local run — nothing left to exercise here");

  await expect(page.getByText("Welcome to TV Home")).toBeVisible();
  await expect(page.locator(".first-run-dot.is-active")).toHaveCount(1);

  // Welcome -> Wi-Fi
  await page.getByText("Get started").click();
  await expect(page.getByRole("heading", { name: "Wi-Fi" })).toBeVisible();

  // Back returns to Welcome rather than falling through to "close an overlay".
  await page.keyboard.press("Escape");
  await expect(page.getByText("Welcome to TV Home")).toBeVisible();
  await page.getByText("Get started").click();
  await expect(page.getByRole("heading", { name: "Wi-Fi" })).toBeVisible();

  // Wi-Fi -> Remote
  await page.getByText("Next", { exact: true }).click();
  await expect(page.getByText("Test your remote")).toBeVisible();

  // Remote -> Apps, via its own "press OK to continue" tile.
  await page.getByText("Press OK to continue").click();
  await expect(page.getByText("Pick a few apps")).toBeVisible();

  // The Home key always returns to Home (Y1's own rule), even mid-setup —
  // treated as "skip the rest of the wizard" rather than a dead end.
  await page.keyboard.press("Home");
  await expect(page.locator(".top-bar")).toBeVisible();
  await expect(page.locator(".first-run")).toHaveCount(0);

  await page.reload();
  await expect(page.locator(".first-run")).toHaveCount(0);
  await expect(page.locator(".top-bar")).toBeVisible();
});
