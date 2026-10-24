import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
test.use({ reducedMotion: 'reduce' });

// Fixed first real/AI entries, selected before reading any model predictions.
const datasetRoot = ['v3','v2','v1'].map(v => '../datasets/prepared/tiny-genimage-' + v).find(root => existsSync(root + '/manifest.csv')) || '../datasets/prepared/tiny-genimage-v1';
const manifestPath = datasetRoot + '/manifest.csv';
const lines = existsSync(manifestPath) ? readFileSync(manifestPath, 'utf8').trim().split(/\r?\n/) : [];
const columns = (lines.shift() || '').split(',');
const records = lines.map(line => Object.fromEntries(line.split(',').map((value, i) => [columns[i], value])));

for (const [label, name] of [['0', 'natural'], ['1', 'synthetic']]) {
  test(`trained detector: ${name} upload, evidence, export and responsive report`, async ({ page }) => {
    test.setTimeout(180000);
    test.skip(!records.length, 'Prepare the public research subset first');
    const sample = records.find(row => row.split === 'test' && row.label === label)!;
    await page.goto('/analyze', { waitUntil: 'domcontentloaded' });
    await page.getByRole('tab', { name: 'Upload a file' }).click();
    await page.locator('input[type=file]').setInputFiles(resolve(datasetRoot, sample.path));
    await page.getByRole('button', { name: 'Analyze Threat' }).click();
    await expect(page).toHaveURL(/analysis\//);
    await expect(page.getByText(/AI-generated probability:/)).toBeVisible({ timeout: 150000 });
    const id = page.url().split('/').pop();
    const row = await (await page.request.get('/api/v1/analyses/' + id)).json();
    const model = row.report.evidence.find((e: any) => e.source === 'image_detector');
    expect(model.label).not.toBe('unavailable');
    expect(model.metadata.calibration).toBe('temperature_scaling');
    if (model.model_version === 'image-detector-v3-community-forensics' && datasetRoot.endsWith('v3')) {
      const evaluated = JSON.parse(readFileSync('../research/experiments/image-community-v3/predictions.json', 'utf8')).test.find((r:any) => r.path === sample.path);
      expect(evaluated).toBeTruthy();
      expect(model.score).toBeCloseTo(evaluated.probability, 5);
    }
    const decisions = model.metadata.stability_checks.map((check: { score: number }) => check.score >= model.metadata.threshold);
    const classChanged = new Set(decisions).size > 1;
    expect(model.metadata.stability_class_changed).toBe(classChanged);
    if (classChanged) {
      expect(model.metadata.unstable).toBe(true);
      expect(model.metadata.verdict).toBe('inconclusive');
      await expect(page.locator('#authenticity-title')).toContainText('Unstable');
    }
    await expect(page.getByText(/AI class cutoff:/)).toBeVisible();
    expect(model.score).toBeGreaterThanOrEqual(0);
    expect(model.score).toBeLessThanOrEqual(1);
    expect(row.report.model_results.some((e: any) => e.id === model.id)).toBe(true);
    expect(row.report.graph.nodes.some((n: any) => n.evidence_id === model.id)).toBe(true);
    expect(row.report.contributions.every((c:any) => !c.evidence_ids.includes(model.id))).toBe(true);
    await page.getByRole('tab', { name: 'models', exact: true }).click();
    await expect(page.getByText(/image_detector · synthetic media/i)).toBeVisible();
    const download = page.waitForEvent('download', {timeout:30000});
    await page.getByRole('button', { name: 'Export JSON' }).click();
    const file = await download;
    const payload = JSON.parse(readFileSync((await file.path())!, 'utf8'));
    expect(payload.image_assessment.score).toBe(model.score);
    expect(payload.report.model_results.find((e: any) => e.id === model.id).metadata.architecture).toBe(model.metadata.architecture);
    await page.getByRole('button', { name: 'Switch to dark mode' }).click();
    await page.screenshot({ path: `../docs/screenshots/trained-image-${name}-dark.png`, fullPage: true });
    expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()).violations).toEqual([]);
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator('.shell')).toHaveClass(/sidebar-collapsed/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../docs/screenshots/trained-image-${name}-mobile.png`, fullPage: true });
    await page.getByRole('button', { name: 'Switch to light mode' }).click();
    expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()).violations).toEqual([]);
    writeFileSync(`../research/results/image-upload-${name}.json`, JSON.stringify({ sample: sample.path, ground_truth: Number(label), report_id: id, model, state: row.state, risk_score: row.report.risk_score, exported: true }, null, 2));
  });
}
