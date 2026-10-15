import test from 'node:test';
import assert from 'node:assert/strict';
import { finiteNumber, normalizeCrop, normalizeRecommendations } from './adapters.js';
import { interpolateYield, scenarioProfit, formatMoney, createRequestGate } from './scenarios.js';

test('missing values stay unavailable, including null and empty strings', () => {
  for (const value of [null, undefined, '', '   ', false, Infinity, NaN, [], {}, Symbol('invalid')]) assert.equal(finiteNumber(value), null);
  assert.equal(formatMoney(null), 'Unavailable');
  const crop = normalizeCrop({ Crop: 'Ragi', Eligible: true, Central_Profit: null });
  assert.equal(crop.Central_Profit, null);
  assert.equal(crop.Eligible, false);
  assert.equal(crop.Yield_q50, null);
  assert.deepEqual(normalizeRecommendations([null, {}, { Crop: '' }]), []);
});
test('yield interpolation recomputes revenue and retains fixed cultivation cost', () => {
  const crop = { Yield_q10: 1, Yield_q50: 2, Yield_q90: 4 };
  assert.equal(interpolateYield(crop, 30), 1.5);
  assert.equal(interpolateYield(crop, 70), 3);
  assert.equal(scenarioProfit(interpolateYield(crop, 50), 100, 500, 2), 3000);
  assert.equal(scenarioProfit(interpolateYield(crop, 10), 100, 500, 2), 1000);
  assert.notEqual(scenarioProfit(1, 100, 500, 2), 3000 * 0.5);
  assert.equal(scenarioProfit(null, 100, 500, 2), null);
  assert.equal(scenarioProfit(1, 100, 500, 0), null);
  assert.equal(interpolateYield({ Yield_q10: 3, Yield_q50: 2, Yield_q90: 4 }, 50), null);
});
test('obsolete request generations cannot update a changed selection', () => {
  const gate = createRequestGate();
  const first = gate.begin();
  gate.invalidate();
  assert.equal(gate.isCurrent(first), false);
  const second = gate.begin();
  assert.equal(gate.isCurrent(second), true);
  const third = gate.begin();
  assert.equal(gate.isCurrent(second), false);
  assert.equal(gate.isCurrent(third), true);
});
