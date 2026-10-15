const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('/Users/manishharigovind/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

const dir = __dirname;
const base = process.env.AGRIINTEL_UI_URL || 'http://127.0.0.1:5174';
const api = process.env.AGRIINTEL_API_URL || 'http://127.0.0.1:8001/api/v2';
const report = { started_at: new Date().toISOString(), base, api, checks: [], console: [], page_errors: [], request_failures: [], http_errors: [], screenshots: [], recommendations: [] };
let browser;
function record(name, evidence) { report.checks.push({ name, status: 'pass', evidence }); console.log(`PASS ${name}`); }
function attach(page, label) {
  page.on('console', (message) => { if (['error', 'warning'].includes(message.type())) report.console.push({ page: label, type: message.type(), message: message.text() }); });
  page.on('pageerror', (error) => report.page_errors.push({ page: label, message: error.message }));
  page.on('requestfailed', (request) => report.request_failures.push({ page: label, url: request.url(), failure: request.failure(), expected_cancel: request.failure()?.errorText === 'net::ERR_ABORTED' }));
  page.on('response', async (response) => {
    if (response.status() >= 400) report.http_errors.push({ page: label, url: response.url(), status: response.status() });
    if (response.url().endsWith('/recommendations') && response.ok()) {
      try { report.recommendations.push({ page: label, request: response.request().postDataJSON(), response: await response.json() }); } catch { /* Response can be cancelled by a location change. */ }
    }
  });
}
async function snapshot(page, name, fullPage = true) {
  const target = path.join(dir, `${name}.png`);
  await page.screenshot({ path: target, fullPage });
  report.screenshots.push(target);
  fs.writeFileSync(path.join(dir, `${name}.txt`), await page.locator('body').innerText());
}
async function loaded(page) {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.locator('#advisory-scenario').waitFor({ state: 'visible' });
  await page.waitForTimeout(2300);
  await page.locator('#aperture-location-btn').click();
  await page.waitForFunction(() => document.querySelector('#state-selector')?.options.length === 6);
  await page.keyboard.press('Escape');
}
async function advice(page) {
  const response = page.waitForResponse((value) => value.url().endsWith('/recommendations') && value.request().method() === 'POST');
  await page.locator('#aperture-submit-btn').click();
  const result = await response;
  assert.equal(result.status(), 200, await result.text());
  const body = await result.json();
  assert.ok(body.recommendations.length > 0);
  await page.getByRole('heading', { name: body.recommendations[0].Crop, exact: true, level: 2 }).waitFor();
  return body;
}
async function feedback(page, participant) {
  const option = await page.locator('#advisory-scenario option').nth(1).getAttribute('value');
  assert.ok(option);
  await page.locator('#advisory-scenario').selectOption(option);
  await page.locator('#demo-participant').fill(participant);
  await page.waitForTimeout(250);
  const body = await advice(page);
  await page.getByRole('button', { name: 'Commit planting', exact: true }).waitFor({ state: 'visible' });
  await page.waitForFunction(() => ![...document.querySelectorAll('button')].find((button) => button.textContent === 'Commit planting')?.disabled);
  return body;
}
function money(value) { return `₹${Math.round(value).toLocaleString('en-IN')}`; }
(async () => {
  try {
    browser = await chromium.launch({ headless: true, args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader'] });
    const contextA = await browser.newContext({ viewport: { width: 1600, height: 1050 } });
    const pageA = await contextA.newPage(); attach(pageA, 'farmer-A');
    await loaded(pageA);
    await snapshot(pageA, '01-historical-standby');
    await pageA.locator('#aperture-location-btn').click();
    const states = await pageA.locator('#state-selector option').evaluateAll((options) => options.map((item) => item.value).filter(Boolean));
    await pageA.keyboard.press('Escape');
    assert.equal(states.length, 5);
    for (let index = 0; index < states.length; index++) {
      const state = states[index];
      await pageA.locator('#aperture-location-btn').click();
      await pageA.locator('#state-selector').selectOption(state);
      const district = await pageA.locator('#district-selector').inputValue();
      assert.ok(district);
      await pageA.keyboard.press('Escape');
      const body = await advice(pageA);
      assert.equal(body.mode, 'historical'); assert.equal(body.data_year, 2019);
      await snapshot(pageA, `02-historical-${index + 1}-${state.replaceAll(' ', '-')}`);
      record(`historical UI ${state}`, { district, rows: body.recommendations.length, artifact_id: body.artifact_id });
    }
    const participantSuffix = Date.now().toString(36);
    const initialA = await feedback(pageA, `qa-a-${participantSuffix}`);
    await snapshot(pageA, '03-feedback-before');
    const crop = initialA.recommendations[0];
    const section = pageA.getByRole('region', { name: `${crop.Crop} recommendation`, exact: true });
    await section.locator('#yield-scenario-slider').focus();
    await pageA.keyboard.press('Home');
    const expectedLow = 10 * crop.Yield_q10 * crop.Price_central - crop.Cost_per_ha;
    await section.getByText(money(expectedLow), { exact: true }).waitFor();
    await section.getByText(money(crop.Cost_per_ha), { exact: true }).waitFor();
    await snapshot(pageA, '04-fixed-cost-slider');
    await section.getByRole('button', { name: 'Reset median' }).click();
    await section.getByText(money(crop.Central_Profit), { exact: true }).waitFor();
    record('yield slider recomputes revenue and fixed cost', { crop: crop.Crop, low_profit: expectedLow, cost_per_ha: crop.Cost_per_ha });
    const contextB = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const pageB = await contextB.newPage(); attach(pageB, 'farmer-B');
    await loaded(pageB);
    const initialB = await feedback(pageB, `qa-b-${participantSuffix}`);
    assert.equal(initialA.revision, initialB.revision);
    const commitResponse = pageA.waitForResponse((response) => response.url().endsWith('/commitments') && response.request().method() === 'POST');
    await pageA.getByRole('button', { name: 'Commit planting', exact: true }).click();
    const committed = await commitResponse; assert.equal(committed.status(), 200, await committed.text());
    const commitResult = await committed.json();
    await pageA.getByRole('button', { name: 'Cancel commitment', exact: true }).waitFor();
    await pageB.getByText(`Ledger revision ${commitResult.revision}`, { exact: true }).waitFor({ timeout: 10000 });
    await pageB.waitForFunction((revision) => document.body.textContent.includes(`Ledger revision ${revision}`), commitResult.revision);
    await pageB.waitForTimeout(500);
    const afterB = report.recommendations.filter((item) => item.page === 'farmer-B' && item.response.mode === 'feedback').at(-1).response;
    assert.equal(afterB.revision, commitResult.revision);
    assert.ok(afterB.recommendations.some((row) => row.Price_central !== initialB.recommendations.find((old) => old.Crop === row.Crop).Price_central));
    await snapshot(pageA, '05-active-commitment');
    await snapshot(pageB, '06-other-farmer-refreshed');
    record('two visible browser contexts share commit and update advice', { crop: crop.Crop, before_revision: initialB.revision, after_revision: afterB.revision });
    const stale = await contextB.request.post(`${api}/commitments`, { data: { scenario_id: initialB.scenario_id, participant_id: `qa-b-${participantSuffix}`, quote_id: initialB.quote_id, crop: initialB.recommendations[0].Crop, idempotency_key: `qa-stale-${participantSuffix}` } });
    assert.equal(stale.status(), 409); record('stale quote rejected after another farmer commits', { status: stale.status(), detail: await stale.json() });
    const cancelResponse = pageA.waitForResponse((response) => response.url().endsWith('/cancel'));
    await pageA.getByRole('button', { name: 'Cancel commitment', exact: true }).click();
    const cancelled = await cancelResponse; assert.equal(cancelled.status(), 200, await cancelled.text());
    const cancelResult = await cancelled.json();
    await pageB.getByText(`Ledger revision ${cancelResult.revision}`, { exact: true }).waitFor({ timeout: 10000 });
    await pageA.waitForFunction(() => ![...document.querySelectorAll('button')].find((button) => button.textContent === 'Commit planting')?.disabled);
    record('cancel releases capacity and refreshes other session', { revision: cancelResult.revision });
    await pageA.getByRole('button', { name: 'Toggle day/night theme' }).click();
    await pageA.waitForTimeout(1500);
    await snapshot(pageA, '07-feedback-night');
    await pageA.getByRole('button', { name: 'Toggle day/night theme' }).click();
    await pageA.waitForTimeout(600);
    const replayCreate = pageA.waitForResponse((response) => response.url().endsWith('/replays') && response.request().method() === 'POST');
    await pageA.getByRole('button', { name: 'Start replay', exact: true }).click();
    const replayResponse = await replayCreate; assert.equal(replayResponse.status(), 200);
    const replay = await replayResponse.json();
    await pageA.getByRole('button', { name: 'Step one farmer' }).click();
    await pageA.getByText('Step 1 / 24 · seed 42', { exact: true }).waitFor();
    await pageA.getByRole('button', { name: 'Play', exact: true }).click();
    await pageA.waitForFunction(() => /Step [3-9] \/ 24/.test(document.body.textContent));
    await pageA.getByRole('button', { name: 'Pause', exact: true }).click();
    await pageA.waitForTimeout(300);
    const pausedRun = await (await contextA.request.get(`${api}/replays/${replay.id}`)).json();
    await pageA.waitForTimeout(1000);
    const pausedAgain = await (await contextA.request.get(`${api}/replays/${replay.id}`)).json();
    assert.equal(pausedRun.step, pausedAgain.step);
    await snapshot(pageA, '08-replay-paused');
    await pageA.getByRole('button', { name: 'Play', exact: true }).click();
    await pageA.getByText('Step 24 / 24 · seed 42 · completed', { exact: true }).waitFor({ timeout: 35000 });
    const finalReplay = await (await contextA.request.get(`${api}/replays/${replay.id}`)).json();
    assert.equal(finalReplay.status, 'completed');
    await pageA.getByText(money(finalReplay.summary.static.total_profit), { exact: true }).waitFor();
    await pageA.getByText(money(finalReplay.summary.dynamic.total_profit), { exact: true }).waitFor();
    await snapshot(pageA, '09-replay-complete');
    report.final_replay = finalReplay;
    record('UI replay start, step, play, pause and completion', { replay_id: replay.id, paused_step: pausedRun.step, total_steps: finalReplay.step, static_profit: finalReplay.summary.static.total_profit, dynamic_profit: finalReplay.summary.dynamic.total_profit });
    await pageA.setViewportSize({ width: 375, height: 812 });
    await pageA.evaluate(() => window.scrollTo(0, 0));
    await pageA.waitForTimeout(500);
    const overflow = await pageA.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth, offenders: [...document.querySelectorAll('body *')].filter((element) => { const rect = element.getBoundingClientRect(); return rect.right > innerWidth + 1 && !element.closest('.overflow-x-auto'); }).slice(0, 20).map((element) => ({ tag: element.tagName, class: element.className?.toString(), right: element.getBoundingClientRect().right })) }));
    await snapshot(pageA, '10-mobile-feedback');
    assert.ok(overflow.document <= 375 && overflow.body <= 375, JSON.stringify(overflow));
    record('375px mobile no page-level horizontal overflow', overflow);
    await pageA.locator('#aperture-area-btn').click();
    await pageA.waitForTimeout(200);
    const areaOverflow = await pageA.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
    await snapshot(pageA, '11-mobile-area-popover');
    assert.ok(areaOverflow.document <= 375, JSON.stringify(areaOverflow));
    await pageA.keyboard.press('Escape');
    await pageA.locator('#advisory-scenario').selectOption('');
    await snapshot(pageA, '12-mobile-historical');
    assert.equal(report.page_errors.length, 0, JSON.stringify(report.page_errors));
    assert.equal(report.console.filter((event) => event.type === 'error').length, 0, JSON.stringify(report.console));
    record('browser runtime has no page or console errors', { page_errors: report.page_errors.length, console_errors: report.console.filter((event) => event.type === 'error').length, warnings: report.console.filter((event) => event.type === 'warning').length });
    report.status = 'pass';
  } catch (error) {
    report.status = 'fail'; report.error = { message: error.message, stack: error.stack };
    console.error(error);
  } finally {
    report.finished_at = new Date().toISOString();
    fs.writeFileSync(path.join(dir, 'browser-e2e-report.json'), JSON.stringify(report, null, 2));
    if (browser) await browser.close();
    if (report.status !== 'pass') process.exitCode = 1;
  }
})();
