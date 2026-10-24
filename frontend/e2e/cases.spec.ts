import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("message investigation, case grouping, historical entities and PDF", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/messages");
  await page
    .getByLabel("Investigation title")
    .fill("Controlled recruitment demonstration");
  await page
    .getByLabel("Message content")
    .fill(
      "Job offer: a registration fee is required before onboarding. Contact recruiter@demo-employer.example. This is a controlled test message.",
    );
  await page
    .getByRole("button", { name: "Investigate message", exact: true })
    .click();
  await expect(page).toHaveURL(/analysis\//);
  await expect(
    page.getByRole("heading", {
      name: "Potential recruitment / payment scam",
      exact: true,
      level: 2,
    }),
  ).toBeVisible({ timeout: 60000 });
  const aid = page.url().split("/").pop()!;
  const row = await (await page.request.get("/api/v1/analyses/" + aid)).json();
  expect(
    row.report.scenarios.some(
      (s: any) => s.scenario_name === "recruitment_scam",
    ),
  ).toBe(true);
  const download = page.waitForEvent("download");
  await page.getByText("Export PDF", { exact: true }).click();
  expect((await download).suggestedFilename()).toContain(".pdf");
  await page.goto("/cases");
  await page.getByLabel("New case title").fill("Job Offer Investigation");
  await page.getByRole("button", { name: "Create case", exact: true }).click();
  await expect(page).toHaveURL(/cases\//);
  const cid = page.url().split("/").pop()!;
  await page.getByLabel("Tags (comma separated)").fill("recruitment, demo");
  await page.getByRole("button", { name: "Save case", exact: true }).click();
  await page.getByRole("tab", { name: "Analyses", exact: true }).click();
  await page.getByLabel("Add an existing investigation").selectOption(aid);
  await page.getByRole("button", { name: "Add to case", exact: true }).click();
  await expect(
    page.locator("table").getByText("Controlled recruitment demonstration.txt"),
  ).toBeVisible();
  await page.getByRole('tab', { name: 'Threat graph', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Interactive investigation graph' })).toBeVisible();
  await expect(page.locator('#node-select option').filter({hasText:'demo-employer.example'}).first()).toHaveCount(1);
  await page.screenshot({ path: '../docs/screenshots/case-graph.png', fullPage: true });
  await page.getByRole("tab", { name: "Notes", exact: true }).click();
  await page
    .getByLabel("Investigation note")
    .fill("Verify the recruiter through an independent official channel.");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(page.locator(".case-note")).toContainText(
    "Verify the recruiter",
  );
  await page.getByRole("tab", { name: "Timeline", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "analysis added", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/case-timeline.png",
    fullPage: true,
  });
  const caseDownload = page.waitForEvent("download");
  await page.getByText("Export case PDF", { exact: true }).click();
  expect((await caseDownload).suggestedFilename()).toContain(cid);
  await page.goto("/intelligence");
  await page.getByLabel("Search entities").fill("demo-employer.example");
  await expect(
    page
      .getByRole("link")
      .filter({ hasText: "recruiter@demo-employer.example" }),
  ).toBeVisible();
  await page
    .getByRole("link")
    .filter({ hasText: "recruiter@demo-employer.example" })
    .click();
  await expect(page.locator('a[href="/cases/' + cid + '"]')).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".shell")).toHaveClass(/sidebar-collapsed/);
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: "../docs/screenshots/entity-mobile.png",
    fullPage: true,
  });
  await page.goto("/cases/" + cid);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});
