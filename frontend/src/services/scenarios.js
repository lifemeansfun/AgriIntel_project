import { finiteNumber } from './adapters.js';

export function interpolateYield(crop, position) {
  const low = finiteNumber(crop?.Yield_q10);
  const median = finiteNumber(crop?.Yield_q50);
  const high = finiteNumber(crop?.Yield_q90);
  const value = finiteNumber(position);
  if ([low, median, high, value].some((number) => number === null) || low > median || median > high || value < 10 || value > 90) return null;
  return value <= 50 ? low + ((value - 10) / 40) * (median - low) : median + ((value - 50) / 40) * (high - median);
}
export function scenarioProfit(yieldPerHa, pricePerQuintal, costPerHa, hectares) {
  const values = [yieldPerHa, pricePerQuintal, costPerHa, hectares].map(finiteNumber);
  if (values.some((value) => value === null) || values[0] < 0 || values[1] < 0 || values[2] < 0 || values[3] <= 0) return null;
  return values[3] * (10 * values[0] * values[1] - values[2]);
}
export function formatMoney(value) {
  return finiteNumber(value) === null ? 'Unavailable' : `₹${Math.round(Number(value)).toLocaleString('en-IN')}`;
}
export function formatQuantity(value, digits = 1) {
  return finiteNumber(value) === null ? 'Unavailable' : Number(value).toLocaleString('en-IN', { maximumFractionDigits: digits });
}
/** Invalidate request generations synchronously before a location or identity change. */
export function createRequestGate() {
  let generation = 0;
  return { begin: () => ++generation, invalidate: () => ++generation, isCurrent: (token) => token === generation };
}
