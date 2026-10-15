import { useState, useEffect, useMemo } from 'react';
import { getLocations } from '../services/api';

export function useLocations() {
  const [locations, setLocations] = useState({});
  const [isLoadingLocations, setIsLoadingLocations] = useState(true);
  const [locationsError, setLocationsError] = useState(null);

  const [formData, setFormData] = useState({
    state: '',
    district: '',
    season: '',
    area: 1.0,
  });

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoadingLocations(true);
      setLocationsError(null);
      try {
        const response = await getLocations();
        const data = response.locations;
        if (!isMounted) return;
        setLocations(data);

        // Auto-select first state, district, season as sensible default
        const states = Object.keys(data);
        if (states.length > 0) {
          const firstState = states[0];
          const districts = Object.keys(data[firstState] || {});
          const firstDistrict = districts[0] || '';
          const seasons = data[firstState]?.[firstDistrict] || [];
          const firstSeason = seasons[0] || '';

          setFormData({
            state: firstState,
            district: firstDistrict,
            season: firstSeason,
            area: 1.0,
          });
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('[useLocations] Error loading locations:', err);
        setLocationsError(err.message || 'Failed to load locations');
      } finally {
        if (isMounted) {
          setIsLoadingLocations(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  const states = useMemo(() => Object.keys(locations), [locations]);

  const districts = useMemo(() => {
    if (!formData.state || !locations[formData.state]) return [];
    return Object.keys(locations[formData.state]);
  }, [locations, formData.state]);

  const seasons = useMemo(() => {
    if (!formData.state || !formData.district || !locations[formData.state]?.[formData.district]) {
      return [];
    }
    return locations[formData.state][formData.district];
  }, [locations, formData.state, formData.district]);

  const handleStateChange = (state) => {
    const districtsList = locations[state] ? Object.keys(locations[state]) : [];
    const firstDistrict = districtsList[0] || '';
    const seasonsList = (locations[state] && firstDistrict) ? locations[state][firstDistrict] || [] : [];
    const firstSeason = seasonsList[0] || '';

    setFormData((prev) => ({
      ...prev,
      state,
      district: firstDistrict,
      season: firstSeason,
    }));
  };

  const handleDistrictChange = (district) => {
    const seasonsList = (locations[formData.state] && district) ? locations[formData.state][district] || [] : [];
    const firstSeason = seasonsList[0] || '';

    setFormData((prev) => ({
      ...prev,
      district,
      season: firstSeason,
    }));
  };

  const handleSeasonChange = (season) => {
    setFormData((prev) => ({
      ...prev,
      season,
    }));
  };

  const handleAreaChange = (area) => {
    setFormData((prev) => ({
      ...prev,
      area,
    }));
  };

  return {
    locations,
    formData,
    setFormData,
    states,
    districts,
    seasons,
    isLoadingLocations,
    locationsError,
    handleStateChange,
    handleDistrictChange,
    handleSeasonChange,
    handleAreaChange,
  };
}
