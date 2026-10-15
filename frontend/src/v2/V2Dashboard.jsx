import { useState } from 'react';
import NaturalLanguageAperture from './components/NaturalLanguageAperture';
import StandbyRegionalBiome from './components/StandbyRegionalBiome';
import MonumentalCropSpecimen from './components/MonumentalCropSpecimen';
import CandidateGallery from './components/CandidateGallery';
import ParetoWaveChart from './components/ParetoWaveChart';
import { useTheme } from '../context/useTheme';

export default function V2Dashboard({ formData, states, districts, seasons, onStateChange, onDistrictChange, onSeasonChange, onAreaChange, onFetch, recommendations = [], isFetching, errorMessage, onViewAnalytics, regional, quoteValid, metadata }) {
  const { textPrimary, textSecondary } = useTheme();
  const [selectedName, setSelectedName] = useState(null);
  const activeCrop = recommendations.find((crop) => crop.Crop === selectedName) || recommendations[0];
  return <div className="w-full pb-12 pt-2 relative z-10"><NaturalLanguageAperture formData={formData} states={states} districts={districts} seasons={seasons} onStateChange={onStateChange} onDistrictChange={onDistrictChange} onSeasonChange={onSeasonChange} onAreaChange={onAreaChange} onSubmit={onFetch} isFetching={isFetching} />{regional && <p className={`max-w-5xl mx-auto mb-5 text-xs ${textSecondary}`}>Changing the location or season returns to the historical explorer.</p>}{errorMessage && <p role="alert" className="w-full max-w-5xl mx-auto mb-6 bg-rose-100 text-rose-900 border border-rose-300 rounded-xl p-4 text-sm">{errorMessage}</p>}{isFetching && <p role="status" className={`max-w-5xl mx-auto mb-5 text-sm ${textPrimary}`}>Refreshing historical recommendations…</p>}{metadata && <p className={`max-w-5xl mx-auto mb-5 text-xs break-words ${textSecondary}`}>Data year {metadata.data_year} · {metadata.mode === 'feedback' ? 'Shared feedback scenario' : 'Historical forecast'} · artifact {metadata.artifact_id || 'unavailable'}</p>}{!recommendations.length ? !isFetching && <StandbyRegionalBiome formData={formData} /> : <div className="space-y-8"><MonumentalCropSpecimen key={activeCrop.Crop} crop={activeCrop} rank={recommendations.indexOf(activeCrop) + 1} formData={formData} onViewAnalytics={onViewAnalytics} feedback={regional} quoteValid={quoteValid} onCommit={regional?.commit} busy={regional?.busy} /><div className="max-w-5xl mx-auto"><ParetoWaveChart recommendations={recommendations} activeCrop={activeCrop} onSelectCrop={(crop) => setSelectedName(crop.Crop)} /><CandidateGallery candidates={recommendations} activeCrop={activeCrop} onSelect={(crop) => setSelectedName(crop.Crop)} /></div></div>}</div>;
}
