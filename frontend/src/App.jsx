import React, { useState, Suspense, lazy } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft } from './components/common/Icons';
import { ThemeProvider } from './context/ThemeContext';
import { useTheme } from './context/useTheme';
import ErrorBoundary from './components/common/ErrorBoundary';
import Navbar from './components/layout/Navbar';
import AmbientBackground from './components/layout/AmbientBackground';
import PublicDashboard from './components/PublicDashboard';
import V2Dashboard from './v2/V2Dashboard';
import SplashScreen from './components/layout/SplashScreen';
import { useLocations } from './hooks/useLocations';
import { useRecommendations } from './hooks/useRecommendations';

const AdvancedAnalytics = lazy(() => import('./components/AdvancedAnalytics'));

function AppContent() {
  const { glassClass, textPrimary, textSecondary } = useTheme();
  const [showSplash, setShowSplash] = useState(true);
  const [view, setView] = useState('dashboard');
  const [selectedCrop, setSelectedCrop] = useState(null);

  const [uiVersion, setUiVersion] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('v') === '1') return 'v1';
      if (params.get('v') === '2') return 'v2';
      return localStorage.getItem('agriintel_ui_version') || 'v2';
    }
    return 'v2';
  });

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('agriintel_ui_version', uiVersion);
    }
  }, [uiVersion]);

  const handleSplashComplete = React.useCallback(() => {
    setShowSplash(false);
  }, []);

  const {
    formData,
    states,
    districts,
    seasons,
    handleStateChange,
    handleDistrictChange,
    handleSeasonChange,
    handleAreaChange,
  } = useLocations();

  const {
    recommendations,
    isFetching,
    error,
    fetchRecommendations,
  } = useRecommendations();

  const handleFetch = React.useCallback(() => {
    fetchRecommendations(formData);
  }, [fetchRecommendations, formData]);

  const handleViewAnalytics = React.useCallback((crop) => {
    setSelectedCrop(crop);
    setView('analytics');
  }, []);

  return (
    <>
      <AnimatePresence>
        {showSplash && <SplashScreen onComplete={handleSplashComplete} />}
      </AnimatePresence>

      <AmbientBackground>
        <Navbar uiVersion={uiVersion} setUiVersion={setUiVersion} />

      <div className="flex-1 no-scrollbar overflow-y-auto">
        <AnimatePresence mode="wait">
          {view === 'dashboard' ? (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.35 }}
            >
              <ErrorBoundary title="Public Dashboard">
                {uiVersion === 'v1' ? (
                  <PublicDashboard
                    formData={formData}
                    states={states}
                    districts={districts}
                    seasons={seasons}
                    onStateChange={handleStateChange}
                    onDistrictChange={handleDistrictChange}
                    onSeasonChange={handleSeasonChange}
                    onAreaChange={handleAreaChange}
                    onFetch={handleFetch}
                    recommendations={recommendations}
                    isFetching={isFetching}
                    errorMessage={error}
                    onViewAnalytics={handleViewAnalytics}
                  />
                ) : (
                  <V2Dashboard
                    formData={formData}
                    states={states}
                    districts={districts}
                    seasons={seasons}
                    onStateChange={handleStateChange}
                    onDistrictChange={handleDistrictChange}
                    onSeasonChange={handleSeasonChange}
                    onAreaChange={handleAreaChange}
                    onFetch={handleFetch}
                    recommendations={recommendations}
                    isFetching={isFetching}
                    errorMessage={error}
                    onViewAnalytics={handleViewAnalytics}
                  />
                )}
              </ErrorBoundary>
            </motion.div>
          ) : (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ duration: 0.35 }}
            >
              <button
                type="button"
                onClick={() => {
                  setView('dashboard');
                }}
                className={`${glassClass} mb-6 px-4 py-2.5 rounded-xl flex items-center gap-2 hover:opacity-80 transition-all font-medium ${textPrimary}`}
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Back to Dashboard</span>
              </button>

              <ErrorBoundary title="Advanced Analytics">
                <Suspense
                  fallback={
                    <div className="flex flex-col items-center justify-center py-24 gap-4">
                      <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                      <p className={`text-sm font-medium ${textSecondary}`}>Loading Deep Economic Analytics...</p>
                    </div>
                  }
                >
                  <AdvancedAnalytics crop={selectedCrop} />
                </Suspense>
              </ErrorBoundary>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AmbientBackground>
    </>
  );
}

export default function App() {
  return (
    <ErrorBoundary title="AgriIntel Root Application">
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </ErrorBoundary>
  );
}
