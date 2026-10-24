import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import AxeBuilder from '@axe-core/playwright';

test('URL report keeps experimental predictions separate from risk', async ({ page }) => {
  test.setTimeout(180000);
  await page.goto('/analyze', {waitUntil:'domcontentloaded'});
  await page.locator('input[type=url]').fill('https://leetcode.com/contest/');
  await page.getByRole('button', {name:'Analyze Threat'}).click();
  await expect(page).toHaveURL(/analysis\//);
  await expect(page.locator('#url-assessment-title')).toBeVisible({timeout:150000});
  const id = page.url().split('/').pop();
  const row = await (await page.request.get('/api/v1/analyses/' + id)).json();
  const model = row.report.evidence.find((e:any) => e.source === 'url_detector' && e.score !== null);
  expect(model).toBeTruthy();
  expect(model.severity).toBe('info');
  expect(row.report.excluded_risk_evidence).toContain(model.id);
  expect(row.report.contributions.every((c:any) => !c.evidence_ids.includes(model.id))).toBe(true);
  if (!row.report.contributions.length) {
    expect(row.report.risk_score).toBeNull();
    await expect(page.locator('#url-assessment-title')).toContainText('Not enough reliable evidence');
  }
  await expect(page.getByRole('button', {name:'Run a new URL check'})).toBeVisible();
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:'../docs/screenshots/url-assessment.png',fullPage:true});
  writeFileSync('../research/results/url-risk-smoke.json',JSON.stringify(row,null,2));
});
