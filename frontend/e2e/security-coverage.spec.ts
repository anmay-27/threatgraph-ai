import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { resolve } from 'node:path';
import { writeFileSync } from 'node:fs';

test('HTML upload explains declared sensitive-data exposure and scanner coverage', async ({ page, request }) => {
  test.setTimeout(180000);
  const html = '<!doctype html><html><body><form method="get" action="http://collector.invalid/collect"><input type="password" name="password"><input name="cc-number"></form></body></html>';
  const response = await request.post('/api/v1/analyze/file', { multipart: {file: {name:'collection-review.html',mimeType:'text/html',buffer:Buffer.from(html)}} });
  expect(response.ok()).toBe(true);
  const {id} = await response.json();
  await page.goto('/analysis/' + id);
  await expect(page.getByRole('heading', {name:'What did we actually check?'})).toBeVisible({timeout:120000});
  await expect(page.getByText('Declared data collection', {exact:true})).toBeVisible();
  await expect(page.getByText('GET → http://collector.invalid/collect', {exact:true})).toBeVisible();
  const row = await (await request.get('/api/v1/analyses/' + id)).json();
  expect(row.report.evidence.some((e:any) => e.label === 'unencrypted_data_submission')).toBe(true);
  expect(row.report.evidence.some((e:any) => e.label === 'sensitive_data_in_url')).toBe(true);
  const malware = row.report.checks.find((c:any) => c.id === 'malware');
  expect(['completed','unavailable']).toContain(malware.status);
  if (malware.status === 'unavailable') expect(malware.unavailable_reasons.length).toBeGreaterThan(0);
  await page.screenshot({path:'../docs/screenshots/security-coverage-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('.shell')).toHaveClass(/sidebar-collapsed/);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:'../docs/screenshots/security-coverage-mobile.png',fullPage:true});
  writeFileSync('../research/results/security-coverage-browser.json', JSON.stringify({report_id:id,checks:row.report.checks},null,2));
});

test('nonfacial video is not labelled authentic', async ({page}) => {
  test.setTimeout(180000);
  await page.goto('/analyze');
  await page.getByRole('tab', {name:'Upload a file'}).click();
  await page.locator('input[type=file]').setInputFiles(resolve('../datasets/demo/shapes.avi'));
  await page.getByRole('button', {name:'Analyze Threat'}).click();
  await expect(page.getByRole('heading', {name:'Video authenticity could not be assessed'})).toBeVisible({timeout:120000});
  await expect(page.getByText(/insufficient facial-video coverage/).first()).toBeVisible();
});

test('installed temporal model returns a real score without a verified authenticity claim', async ({page}) => {
  test.setTimeout(240000);
  await page.goto('/analyze');
  await page.getByRole('tab', {name:'Upload a file'}).click();
  await page.locator('input[type=file]').setInputFiles(resolve('../datasets/demo/astronaut-motion.avi'));
  await page.getByRole('button', {name:'Analyze Threat'}).click();
  await expect(page.getByRole('heading', {name:'Visual deepfake screening completed'})).toBeVisible({timeout:210000});
  await expect(page.getByText('Unverified', {exact:true})).toBeVisible();
  const id = page.url().split('/').pop();
  const row = await (await page.request.get('/api/v1/analyses/' + id)).json();
  const model = row.report.evidence.find((e:any) => e.source === 'video_detector');
  expect(model.metadata.sampled_frames).toBe(16);
  expect(model.metadata.risk_eligible).toBe(false);
  expect(model.score).toBeGreaterThanOrEqual(0);
  expect(model.score).toBeLessThanOrEqual(1);
  await page.screenshot({path:'../docs/screenshots/video-screening.png',fullPage:true});
  writeFileSync('../research/results/video-upload-smoke.json', JSON.stringify({report_id:id,model},null,2));
});
