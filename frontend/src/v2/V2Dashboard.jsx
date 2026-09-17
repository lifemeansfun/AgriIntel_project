import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import NaturalLanguageAperture from './components/NaturalLanguageAperture';
import StandbyRegionalBiome from './components/StandbyRegionalBiome';
import MonumentalCropSpecimen from './components/MonumentalCropSpecimen';
import CandidateGallery from './components/CandidateGallery';
import ParetoWaveChart from './components/ParetoWaveChart';
import { AlertTriangle } from '../components/common/Icons';

export default function V2Dashboard({
  formData,
  states,
  districts,
  seasons,
  onStateChange,
  onDistrictChange,
  onSeasonChange,
  onAreaChange,
  onFetch,
  recommendations,
  isFetching,
  errorMessage,
  onViewAnalytics,
}) {
  const [activeCrop, setActiveCrop] = useState(null);

  // When recommendations come in, select the first one as active champion
  useEffect(() => {
    if (recommendations && recommendations.length > 0 && !isFetching) {
      setActiveCrop(recommendations[0]);
    } else if (!recommendations || recommendations.length === 0) {
      setActiveCrop(null);
    }
  }, [recommendations, isFetching]);

  const hasResults = recommendations && recommendations.length > 0;
  const isStandby = !hasResults && !isFetching;

  return (
    <div className="w-full min-h-screen px-4 sm:px-6 lg:px-8 pb-32 pt-8 flex flex-col relative z-10">
      
      {/* 1. Natural Language Aperture Bar (Always visible) */}
      <NaturalLanguageAperture
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

      {/* Error State */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="w-full max-w-5xl mx-auto mb-8 bg-rose-500/10 border border-rose-500/20 text-rose-500 p-4 rounded-xl flex items-start gap-3 backdrop-blur-sm"
          >
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm font-medium">{errorMessage}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {isStandby ? (
          /* 2. Standby Regional Biome */
          <motion.div
            key="standby"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.4 }}
            className="flex-1 w-full"
          >
            <StandbyRegionalBiome formData={formData} />
          </motion.div>
        ) : (
          /* 3. Recommended Frontier State */
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="flex-1 w-full space-y-12"
          >
            {/* The Champion Specimen */}
            {activeCrop && (
              <MonumentalCropSpecimen 
                crop={activeCrop} 
                onViewAnalytics={onViewAnalytics} 
              />
            )}
            
            {/* The Alternative Shelf & Wave */}
            {hasResults && (
              <div className="w-full max-w-5xl mx-auto">
                <ParetoWaveChart 
                  recommendations={recommendations} 
                  onSelectCrop={setActiveCrop} 
                  activeCrop={activeCrop} 
                />
                <CandidateGallery 
                  candidates={recommendations.slice(1)} 
                  onSelect={setActiveCrop}
                  activeCrop={activeCrop}
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
