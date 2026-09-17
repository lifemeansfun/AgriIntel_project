import React from 'react';
import LocationFilterForm from '../features/advisory/LocationFilterForm';
import RecommendationList from '../features/advisory/RecommendationList';
import ErrorBoundary from './common/ErrorBoundary';
import { AlertTriangle } from './common/Icons';

export default function PublicDashboard({
  formData,
  states = [],
  districts = [],
  seasons = [],
  onStateChange,
  onDistrictChange,
  onSeasonChange,
  onAreaChange,
  onFetch,
  recommendations = [],
  isFetching = false,
  errorMessage = null,
  onViewAnalytics,
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-16">
      {/* Left Column: Form Panel */}
      <div className="lg:col-span-4">
        <ErrorBoundary title="Location Filter Form">
          <LocationFilterForm
            formData={formData}
            states={states}
            districts={districts}
            seasons={seasons}
            onStateChange={onStateChange}
            onDistrictChange={onDistrictChange}
            onSeasonChange={onSeasonChange}
            onAreaChange={onAreaChange}
            onSubmit={onFetch}
            isFetching={isFetching}
          />
        </ErrorBoundary>
      </div>

      {/* Right Column: Recommendations Leaderboard */}
      <div className="lg:col-span-8">
        {errorMessage && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-200 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <p className="text-sm">{errorMessage}</p>
          </div>
        )}
        <ErrorBoundary title="Recommendations Leaderboard">
          <RecommendationList
            recommendations={recommendations}
            formData={formData}
            onSelectCrop={onViewAnalytics}
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
