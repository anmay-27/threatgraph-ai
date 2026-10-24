import { chromium } from '@playwright/test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
const extension = resolve('../browser-extension');
const profile = mkdtempSync(resolve(tmpdir(), 'threatgraph-extension-'));
try {
  const context = await chromium.launchPersistentContext(profile, {
    channel: 'msedge',
    headless: true,
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  try {
    let workers = context.serviceWorkers();
    if (!workers.length) workers = [await context.waitForEvent('serviceworker', {timeout:15000})];
    const id = new URL(workers[0].url()).host;
    await workers[0].evaluate(() => chrome.storage.session.set({selectedUrl:'https://example.com/'}));
    const page = await context.newPage();
    await page.setViewportSize({width:360,height:520});
    await page.goto(`chrome-extension://${id}/popup.html`);
    await page.locator('#url').waitFor();
    await page.getByRole('button',{name:'Analyze with ThreatGraph'}).click();
    await page.locator('#report:not([hidden])').waitFor({timeout:30000});
    await page.waitForFunction(() => document.querySelector('#status')?.textContent?.includes('Risk:'), {timeout:90000});
    await page.screenshot({path:'../docs/screenshots/browser-extension.png'});
    console.log({ extension_id: id, popup_title: await page.title(), submit_button: await page.locator('#analyze').count() });
    if ((await page.locator('#analyze').count()) !== 1) throw new Error('Extension popup missing action');
  } finally { await context.close(); }
} finally { rmSync(profile, {recursive:true,force:true}); }
