import axios from 'axios';
import { normalizeRecommendations, normalizeLocations } from './adapters';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
});

export const getLocations = async () => {
  try {
    const response = await apiClient.get('/locations');
    return normalizeLocations(response.data);
  } catch (error) {
    console.error('[API Error] Failed to fetch locations:', error);
    throw error;
  }
};

export const getRecommendations = async (params) => {
  try {
    const response = await apiClient.post('/recommendations', params);
    const rawList = response.data?.recommendations ?? [];
    return normalizeRecommendations(rawList);
  } catch (error) {
    console.error('[API Error] Failed to fetch recommendations:', error);
    throw error;
  }
};

export default apiClient;
