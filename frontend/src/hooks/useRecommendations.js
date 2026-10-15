import { useState, useCallback, useRef, useEffect } from 'react';
import { getRecommendations, apiErrorMessage } from '../services/api';
import { createRequestGate } from '../services/scenarios';

export function useRecommendations() {
  const [result, setResult] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState(null);
  const gate = useRef(createRequestGate());
  const controller = useRef(null);
  const invalidate = useCallback(() => {
    gate.current.invalidate();
    controller.current?.abort();
    setResult(null);
    setError(null);
    setIsFetching(false);
  }, []);
  useEffect(() => () => { gate.current.invalidate(); controller.current?.abort(); }, []);
  const fetchRecommendations = useCallback(async (formData, extras = {}) => {
    const area = Number(formData.area);
    if (!formData.state || !formData.district || !formData.season || !Number.isFinite(area) || area <= 0) {
      setError('Choose a location, season and a positive land area.');
      return null;
    }
    controller.current?.abort();
    controller.current = new AbortController();
    const request = gate.current.begin();
    setIsFetching(true);
    setError(null);
    try {
      const data = await getRecommendations({ state: formData.state, district: formData.district, season: formData.season, area_hectares: area, ...extras }, controller.current.signal);
      if (!gate.current.isCurrent(request)) return null;
      setResult(data);
      if (!data.recommendations.length) setError('No eligible historical forecasts are available for this selection.');
      return data;
    } catch (err) {
      if (!gate.current.isCurrent(request) || err.code === 'ERR_CANCELED') return null;
      setError(apiErrorMessage(err));
      return null;
    } finally {
      if (gate.current.isCurrent(request)) setIsFetching(false);
    }
  }, []);
  return { result, recommendations: result?.recommendations || [], isFetching, error, fetchRecommendations, clearRecommendations: invalidate };
}
