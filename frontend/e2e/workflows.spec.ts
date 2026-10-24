import { test, expect } from "@playwright/test";

test("upload, investigation, graph, persistent history and pages", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("heading", { name: /Analyze digital content/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/analyze-desktop.png",
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Upload a file" }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "safe-notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "ThreatGraph local integration sample. No live threats.",
    ),
  });
  await page.getByRole("button", { name: "Analyze Threat" }).click();
  await expect(page).toHaveURL(/analysis\//);
  await expect(
    page.getByRole("heading", { name: "Investigation graph" }),
  ).toBeVisible({ timeout: 45000 });
  await expect(page.getByText("inconclusive", { exact: true })).toBeVisible();
  await page.getByLabel("Inspect a node").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Trace incoming paths" }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../docs/screenshots/report-desktop.png",
    fullPage: true,
  });
  for (const tab of ["models", "provenance", "technical", "evidence"])
    await page.getByRole("tab", { name: tab, exact: true }).click();
  for (const route of [
    "/history",
    "/dashboard",
    "/research/models",
    "/about/methodology",
  ]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.getByRole("status")).toHaveCount(0);
    await page.screenshot({
      path: "../docs/screenshots/" + route.replaceAll("/", "-") + ".png",
      fullPage: true,
    });
  }
  await page.goto("/history", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("link", { name: "safe-notes.txt" }).first(),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.screenshot({
    path: "../docs/screenshots/analyze-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("unsafe URL returns an actionable error", async ({ page }) => {
  await page.goto("/analyze", { waitUntil: "domcontentloaded" });
  await page.getByLabel("Where should we start?").fill("http://127.0.0.1/");
  await page.getByRole("button", { name: "Analyze Threat" }).click();
  await expect(page.getByRole("alert")).toContainText("Non-public");
});
