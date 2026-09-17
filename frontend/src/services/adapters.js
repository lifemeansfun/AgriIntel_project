/**
 * Defensive data adapter to normalize API responses.
 * Protects components from null, undefined, or unexpected shapes.
 */

export function normalizeCrop(raw) {
  if (!raw || typeof raw !== 'object') {
    return {
      Crop: 'Unknown',
      Score: 0,
      Expected_Profit: 0,
      Downside_Risk: 0,
      Cost_per_ha: 0,
      Safety_Rating: 'Moderate Risk',
      Yield_q10: 0,
      Yield_q50: 0,
      Yield_q90: 0,
      Price_p10: 0,
      Price_p50: 0,
      Price_p90: 0,
    };
  }

  return {
    Crop: String(raw.Crop ?? 'Unknown'),
    Score: Number(raw.Score ?? 0),
    Expected_Profit: Number(raw.Expected_Profit ?? 0),
    Downside_Risk: Number(raw.Downside_Risk ?? 0),
    Cost_per_ha: Number(raw.Cost_per_ha ?? 0),
    Safety_Rating: String(raw.Safety_Rating ?? 'Moderate Risk'),
    Yield_q10: Number(raw.Yield_q10 ?? 0),
    Yield_q50: Number(raw.Yield_q50 ?? 0),
    Yield_q90: Number(raw.Yield_q90 ?? 0),
    Price_p10: Number(raw.Price_p10 ?? 0),
    Price_p50: Number(raw.Price_p50 ?? 0),
    Price_p90: Number(raw.Price_p90 ?? 0),
  };
}

export function normalizeRecommendations(list) {
  if (!Array.isArray(list)) return [];
  return list.map(normalizeCrop);
}

export function normalizeLocations(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {};
  }
  return raw;
}
