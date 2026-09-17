import { useState, useCallback, useRef } from 'react';
import { getRecommendations } from '../services/api';

export function useRecommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState(null);

  // In-memory cache keyed by "state:district:season:area" for 0ms instant UI transitions
  const cacheRef = useRef(new Map());

  const fetchRecommendations = useCallback(async (formData) => {
    if (!formData.state || !formData.district || !formData.season) {
      return;
    }

    const area = parseFloat(formData.area) || 1.0;
    const cacheKey = `${formData.state}:${formData.district}:${formData.season}:${area}`;

    // Instant SWR: if already in cache, serve immediately without loading flicker
    if (cacheRef.current.has(cacheKey)) {
      const cached = cacheRef.current.get(cacheKey);
      setRecommendations(cached);
      setError(null);
      return cached;
    }

    setIsFetching(true);
    setError(null);

    try {
      const recs = await getRecommendations({
        state: formData.state,
        district: formData.district,
        season: formData.season,
        area_hectares: area,
      });
      cacheRef.current.set(cacheKey, recs);
      setRecommendations(recs);
      return recs;
    } catch (err) {
      const message = err?.response?.data?.detail || err.message || 'Failed to fetch recommendations';
      setError(message);
      console.error('[useRecommendations] Error:', err);
    } finally {
      setIsFetching(false);
    }
  }, []);

  const clearRecommendations = useCallback(() => {
    setRecommendations([]);
    setError(null);
  }, []);

  return {
    recommendations,
    isFetching,
    error,
    fetchRecommendations,
    clearRecommendations,
  };
}
