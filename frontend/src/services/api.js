import axios from 'axios';
import { normalizeRecommendations, normalizeLocations } from './adapters.js';

const configuredBase = (import.meta.env?.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');
const apiClient = axios.create({ baseURL: configuredBase.endsWith('/v2') ? configuredBase : `${configuredBase}/v2`, timeout: 20000 });

export const getLocations = async () => {
  const { data } = await apiClient.get('/locations');
  return { ...data, locations: normalizeLocations(data?.locations) };
};
export const getRecommendations = async (params, signal) => {
  const { data } = await apiClient.post('/recommendations', params, { signal });
  return { ...data, recommendations: normalizeRecommendations(data?.recommendations) };
};
export const getScenarios = async () => (await apiClient.get('/scenarios')).data;
export const getScenarioState = async (scenarioId, participantId) => (await apiClient.get('/state', { params: { scenario_id: scenarioId, participant_id: participantId } })).data;
export const createCommitment = async (body) => (await apiClient.post('/commitments', body)).data;
export const cancelCommitment = async (id, body) => (await apiClient.post(`/commitments/${encodeURIComponent(id)}/cancel`, body)).data;
export const createReplay = async (seed) => (await apiClient.post('/replays', { seed })).data;
export const getReplay = async (id) => (await apiClient.get(`/replays/${encodeURIComponent(id)}`)).data;
export const stepReplay = async (id) => (await apiClient.post(`/replays/${encodeURIComponent(id)}/step`)).data;
export function apiErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join('; ');
  return error?.message || 'The request could not be completed. Please retry.';
}
export default apiClient;
