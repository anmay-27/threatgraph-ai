import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { writeFileSync } from 'node:fs';

for (const theme of ["light", "dark"]) {
test(`${theme}: required pages have no detected WCAG A/AA violations`, async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.addInitScript((value) => localStorage.setItem("threatgraph-theme", value), theme);
  const failures: unknown[] = [];
  const routes = [
    "/analyze",
    "/dashboard",
    "/history",
    "/research/models",
    "/about/methodology",
  ];
  const history = await (await page.request.get('/api/v1/history')).json();
  const completed = history.find((row: {state:string}) => ['COMPLETED','PARTIAL'].includes(row.state));
  if (completed) routes.push('/analysis/'+completed.id);
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.getByRole("status")).toHaveCount(0);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    if (result.violations.length)
      failures.push({
        route,
        violations: result.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => ({
            target: n.target,
            summary: n.failureSummary,
          })),
        })),
      });
  }
  await page.setViewportSize({width:390,height:844});
  await page.goto('/analyze');
  await expect(page.locator('h1')).toBeVisible();
  const mobile = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
  if (mobile.violations.length) failures.push({route:'/analyze (mobile)',violations:mobile.violations});
  writeFileSync(`../research/results/accessibility-${theme}.json`,JSON.stringify({routes,mobile:true,failures},null,2));
  expect(failures).toEqual([]);
});
}
