import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe.configure({ mode: 'serial' });

test('annotate, select exact Unicode evidence, complete, duplicate, reload, and export', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('pageerror', error => consoleErrors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  if (await page.getByLabel('Your name', { exact: true }).isVisible()) {
    await page.getByLabel('Your name', { exact: true }).fill('Browser Researcher');
    await page.getByRole('button', { name: 'Start annotating' }).click();
  }
  await page.getByLabel('Add or open a PMID').fill('123');
  await page.getByRole('button', { name: 'Open', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('A fictional article for interface testing');
  await page.getByRole('button', { name: 'New observation', exact: true }).click();
  await page.getByLabel('Mutation *', { exact: true }).fill('TEST:A1G');
  await page.getByLabel('Phenotype *', { exact: true }).fill('No observed difference');
  const passage = page.locator('.passage').filter({ has: page.getByText('An observed difference. α🙂 An observed difference.', { exact: true }) });
  await passage.locator('p').evaluate(element => {
    const node = element.firstChild!;
    const text = node.textContent!;
    const start = text.lastIndexOf('An observed difference.');
    const range = document.createRange(); range.setStart(node, start); range.setEnd(node, text.length);
    window.getSelection()!.removeAllRanges(); window.getSelection()!.addRange(range);
  });
  await passage.getByRole('button', { name: 'Attach Results evidence' }).click();
  await expect(page.locator('.evidence blockquote')).toHaveText('An observed difference.');
  await page.getByRole('button', { name: 'Mark complete', exact: true }).click();
  await expect(page.locator('.editor .badge')).toHaveText('complete');
  await expect(page.locator('.save-strip')).toContainText('Saved');
  await page.getByRole('button', { name: 'Show in article' }).click();
  await expect(passage).toHaveClass(/highlighted/);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: '../.artifacts/annotation-workspace.png' });
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole('button', { name: 'Duplicate observation' }).click();
  await expect(page.locator('.editor .badge')).toHaveText('draft');
  await expect(page.locator('.evidence blockquote')).toHaveCount(0);
  await expect(page.getByLabel('Mutation *', { exact: true })).toHaveValue('TEST:A1G');
  await page.getByLabel('Phenotype *', { exact: true }).fill('A second observation');
  await page.getByRole('button', { name: 'Save now' }).click();
  await expect(page.locator('.save-strip')).toContainText('Saved');
  await page.reload();
  await page.getByRole('button', { name: /PMID 123/ }).click();
  await expect(page.getByRole('combobox', { name: 'Observation', exact: true }).locator('option')).toHaveCount(3);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export work', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('iav-annotations.zip');
  expect(consoleErrors).toEqual([]);
});

test('abstract-only papers support notes and deferral, and narrow screens fit', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Add or open a PMID').fill('124');
  await page.getByRole('button', { name: 'Open', exact: true }).click();
  await expect(page.getByRole('button', { name: 'New observation', exact: true })).toBeDisabled();
  await page.getByText('Paper progress and screening notes').click();
  await page.getByLabel('Paper progress', { exact: true }).selectOption('deferred');
  await page.getByLabel('Screening notes', { exact: true }).fill('Full text needed before annotation.');
  await page.getByRole('button', { name: 'Save paper notes' }).click();
  await expect(page.locator('.paper-notes summary')).toContainText('Saved');
  for (const width of [320, 768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.screenshot({ path: '../.artifacts/annotation-mobile.png', fullPage: true });
  await page.reload();
  await page.getByRole('button', { name: /PMID 124/ }).click();
  await page.getByText('Paper progress and screening notes').click();
  await expect(page.getByLabel('Paper progress', { exact: true })).toHaveValue('deferred');
  await expect(page.getByLabel('Screening notes', { exact: true })).toHaveValue('Full text needed before annotation.');
});

test('repository import can be previewed and applied in the interface', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Import & backup' }).click();
  await page.getByRole('button', { name: 'Preview existing repository annotations' }).click();
  await expect(page.getByRole('heading', { name: /brian_annotations.csv: 8 rows/ })).toBeVisible();
  await page.getByRole('button', { name: 'Import previewed rows' }).click();
  await expect(page.getByRole('dialog').getByRole('status')).toContainText('66 imported; 0 already present.');
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.getByRole('button', { name: /PMID 25210184/ })).toBeVisible();
});

test('typing during a save retains later edits, and stale-tab edits stay visible', async ({ page, request }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /PMID 123 / }).click();
  await page.getByRole('button', { name: 'New observation', exact: true }).click();
  await page.route('**/api/observations/*', async route => {
    if (route.request().method() === 'PUT') await new Promise(resolve => setTimeout(resolve, 250));
    await route.continue();
  });
  await page.getByLabel('Mutation *', { exact: true }).fill('TEST:A2G');
  await page.getByRole('button', { name: 'Save now' }).click();
  await page.getByLabel('Phenotype *', { exact: true }).fill('Written during the save');
  await expect(page.locator('.save-strip')).toContainText('Saved');
  const rows = await (await request.get('/api/papers/123/observations')).json();
  const row = rows.find((item: { fields: { mutation: string } }) => item.fields.mutation === 'TEST:A2G');
  expect(row.fields.phenotype).toBe('Written during the save');
  row.fields.notes = 'Changed from a second tab';
  expect((await request.put(`/api/observations/${row.id}`, { data: row })).ok()).toBe(true);
  await page.getByLabel('Phenotype *', { exact: true }).fill('Keep this unsaved text');
  await page.getByRole('button', { name: 'Save now' }).click();
  await expect(page.getByRole('alert')).toContainText('changed in another tab');
  await expect(page.getByLabel('Phenotype *', { exact: true })).toHaveValue('Keep this unsaved text');
  await expect(page.getByRole('button', { name: 'Mark complete', exact: true })).toBeDisabled();
  page.on('dialog', dialog => dialog.accept()); // discard only this isolated browser-test tab
});

test('a failed completion can still be saved and exported as partial work', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /PMID 123 / }).click();
  await page.getByRole('button', { name: 'New observation', exact: true }).click();
  await page.getByRole('button', { name: 'Mark complete', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Results evidence is required');
  await page.getByRole('button', { name: 'Save as draft', exact: true }).click();
  await expect(page.locator('.save-strip')).toContainText('Saved');
  await expect(page.locator('.editor .badge')).toHaveText('draft');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export work', exact: true }).click();
  await download;
});
