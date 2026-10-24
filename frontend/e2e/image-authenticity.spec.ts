import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("updated image report explains evidence and stability", async ({ page }) => {
  test.skip(!process.env.STABILITY_REPORT_ID, "Optional retained image report");
  await page.goto("/analysis/" + process.env.STABILITY_REPORT_ID, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "What was actually detected?" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Overall investigation coverage" })).toBeVisible();
  await page.getByText("Explore prediction stability", { exact: true }).click();
  await expect(page.getByText("Horizontal flip", { exact: true })).toBeVisible();
  await expect(page.getByText("JPEG quality 85", { exact: true })).toBeVisible();
});

test("retained document report displays model suggestion with scope caution", async ({ page }) => {
  test.skip(!process.env.IMAGE_REPORT_ID, "Optional local document report");
  await page.goto("/analysis/" + process.env.IMAGE_REPORT_ID);
  await expect(page.getByRole("heading", { name: "Document-like image — AI origin remains uncertain" })).toBeVisible();
  await expect(page.getByText(/AI model score:/)).toBeVisible();
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
});

test("image upload shows a real local classifier suggestion", async ({ page }) => {
  test.setTimeout(180000);
  const models = await (await page.request.get("/api/v1/models")).json();
  test.skip(!models.some((m: { name: string; available: boolean }) => m.name === "image" && m.available), "Install the image checkpoint first");
  await page.goto("/analyze", { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Upload a file" }).click();
  await page.locator("input[type=file]").setInputFiles("../datasets/demo/illustration.png");
  await page.getByRole("button", { name: "Analyze Threat" }).click();
  await expect(page).toHaveURL(/analysis\//);
  await expect(page.getByText(/AI model score:|AI-generated probability:/)).toBeVisible({ timeout: 150000 });
  await expect(page.locator("#authenticity-title")).toBeVisible();
  await expect(page.getByRole("heading", { name: "How should I verify it?" })).toBeVisible();
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
  await page.screenshot({ path: "../docs/screenshots/image-authenticity.png", fullPage: true });
});
