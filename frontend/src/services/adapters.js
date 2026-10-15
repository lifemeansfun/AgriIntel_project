/** Missing financial/forecast values remain unavailable; never turn them into money. */
export function finiteNumber(value) {
  if (!['number', 'string'].includes(typeof value) || (typeof value === 'string' && !value.trim())) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

const NUMERIC_FIELDS = [
  'Score', 'Central_Profit', 'Pessimistic_Profit', 'Downside_Gap', 'Cost_per_ha',
  'Yield_q10', 'Yield_q50', 'Yield_q90', 'Price_pessimistic', 'Price_central',
  'Price_optimistic', 'Remaining_Area_ha',
];
export function normalizeCrop(raw) {
  if (!raw || typeof raw !== 'object' || typeof raw.Crop !== 'string' || !raw.Crop.trim()) return null;
  const crop = { ...raw, Crop: raw.Crop.trim() };
  for (const key of NUMERIC_FIELDS) crop[key] = finiteNumber(raw[key]);
  const present = NUMERIC_FIELDS.filter((key) => key !== 'Remaining_Area_ha').every((key) => crop[key] !== null);
  const complete = present && crop.Yield_q10 >= 0 && crop.Yield_q10 <= crop.Yield_q50 && crop.Yield_q50 <= crop.Yield_q90 && crop.Cost_per_ha >= 0 && crop.Downside_Gap >= 0 && crop.Price_pessimistic >= 0 && crop.Price_central >= 0 && crop.Price_optimistic >= 0;
  crop.Eligible = raw.Eligible === true && complete;
  crop.Ineligibility_Reason = complete ? String(raw.Ineligibility_Reason || '') : 'Required forecast or economic values are unavailable.';
  return crop;
}
export function normalizeRecommendations(list) {
  return Array.isArray(list) ? list.map(normalizeCrop).filter(Boolean) : [];
}
export function normalizeLocations(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  return raw;
}
