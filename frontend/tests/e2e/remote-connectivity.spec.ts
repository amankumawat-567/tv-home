import { expect, request, test } from "@playwright/test";

const BACKEND_URL = "http://127.0.0.1:8000";

// Both flows below mutate shared mock backend state (one process for the
// whole suite, across both viewport projects — see playwright.config.ts) --
// each uses a device nothing else in the suite touches, but still only
// reaches its "freshly unpaired" starting point once per run; a second
// project hitting an already-mutated device skips rather than re-asserting
// a start state that's no longer there (same pattern as first-run.spec.ts).

test.describe("Bluetooth pairing-agent prompts", () => {
  test.beforeAll(async () => {
    const api = await request.newContext();
    await api.post(`${BACKEND_URL}/api/first-run/complete`);
    await api.dispose();
  });

  test("a PIN-only device prompts for a PIN via the on-screen keyboard", async ({ page }) => {
    const api = await request.newContext();
    const before = await (await api.get(`${BACKEND_URL}/api/bluetooth`)).json();
    const device = before.devices.find((d: { mac: string }) => d.mac === "AA:BB:CC:00:11:55");
    test.skip(!device || device.paired, "already paired by an earlier project run in this backend process");
    await api.dispose();

    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await page.keyboard.press("m");
    await page.getByText("Settings", { exact: true }).click();
    await page.getByText("Bluetooth", { exact: true }).click();
    await page.getByText("Old Bluetooth Keyboard", { exact: true }).click();

    await expect(page.locator(".keyboard-label")).toHaveText("PIN for Old Bluetooth Keyboard");
    for (const ch of "0000") {
      await page.locator(".keyboard-key", { hasText: ch }).first().click();
    }
    await page.locator(".keyboard-key.is-accent", { hasText: "Pair" }).click();

    await expect(page.locator(".toast")).toHaveText("Old Bluetooth Keyboard connected.");
  });

  test("a numeric-comparison device prompts for yes/no confirmation", async ({ page }) => {
    const api = await request.newContext();
    const before = await (await api.get(`${BACKEND_URL}/api/bluetooth`)).json();
    const device = before.devices.find((d: { mac: string }) => d.mac === "AA:BB:CC:00:11:66");
    test.skip(!device || device.paired, "already paired by an earlier project run in this backend process");
    await api.dispose();

    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await page.keyboard.press("m");
    await page.getByText("Settings", { exact: true }).click();
    await page.getByText("Bluetooth", { exact: true }).click();
    await page.getByText("Car Stereo", { exact: true }).click();

    await expect(page.locator(".dialog-title")).toHaveText("Confirm pairing code");
    await expect(page.locator(".dialog-message")).toHaveText("Does Car Stereo show 583921?");
    await page.getByText("Yes, it matches", { exact: true }).click();

    await expect(page.locator(".toast")).toHaveText("Car Stereo connected.");
  });
});

test.describe("KDE Connect remote pairing", () => {
  test("shows reachable/paired/incoming devices and supports both pairing directions", async ({ page }) => {
    const api = await request.newContext();
    const before = await (await api.get(`${BACKEND_URL}/api/kdeconnect`)).json();
    const pixel = before.devices.find((d: { id: string }) => d.id === "dev-pixel");
    const oldPhone = before.devices.find((d: { id: string }) => d.id === "dev-old-phone");
    test.skip(!pixel || pixel.paired || !oldPhone?.incomingRequest, "already mutated by an earlier project run");
    await api.dispose();

    await page.goto("/");
    await page.waitForSelector(".top-bar");
    await page.keyboard.press("m");
    await page.getByText("Settings", { exact: true }).click();
    await page.getByText("Remote connect", { exact: true }).click();
    await expect(page.locator(".settings-title")).toHaveText("Remote connect (KDE Connect)");

    // Box-initiated: pair with the reachable-but-unpaired phone.
    await page.getByText("Aman's Pixel", { exact: true }).click();
    await expect(page.locator(".toast")).toHaveText("Paired with Aman's Pixel.");

    // Phone-initiated: accept the incoming request from the other device.
    await page.getByText("Old Phone", { exact: true }).click();
    await expect(page.locator(".toast").last()).toHaveText("Paired with Old Phone.");
  });
});
