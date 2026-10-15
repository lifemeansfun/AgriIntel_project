import { useState, useEffect, useCallback, Suspense, lazy } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ChevronLeft } from './components/common/Icons';
import { ThemeProvider } from './context/ThemeContext';
import { useTheme } from './context/useTheme';
import ErrorBoundary from './components/common/ErrorBoundary';
import Navbar from './components/layout/Navbar';
import AmbientBackground from './components/layout/AmbientBackground';
import V2Dashboard from './v2/V2Dashboard';
import SplashScreen from './components/layout/SplashScreen';
import RegionalFeedbackPanel from './features/advisory/RegionalFeedbackPanel';
import ClassroomReplay from './features/advisory/ClassroomReplay';
import { useLocations } from './hooks/useLocations';
import { useRecommendations } from './hooks/useRecommendations';
import { useRegionalAdvisory } from './hooks/useRegionalAdvisory';

const AdvancedAnalytics = lazy(() => import('./components/AdvancedAnalytics'));

function AppContent() {
  const { glassClass, textPrimary, textSecondary } = useTheme();
  const [showSplash, setShowSplash] = useState(true);
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [now, setNow] = useState(() => Date.now());
  const locations = useLocations();
  const advisory = useRecommendations();
  const regional = useRegionalAdvisory({ formData: locations.formData, setFormData: locations.setFormData, advisory });
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const handleSplashComplete = useCallback(() => setShowSplash(false), []);
  const expiryRaw = Number(advisory.result?.quote_expires_at);
  const expiry = expiryRaw < 1e12 ? expiryRaw * 1000 : expiryRaw;
  const quoteValid = Boolean(advisory.result?.quote_id && expiry > now && regional.state && !regional.stateError && advisory.result.revision === regional.state.revision && advisory.result.scenario_id === regional.scenarioId);
  const changeLocation = (handler, value) => {
    advisory.clearRecommendations();
    regional.selectScenario('');
    setSelectedCrop(null);
    handler(value);
  };
  const cropForAnalytics = advisory.recommendations.find((crop) => crop.Crop === selectedCrop?.Crop) || selectedCrop;
  return <><AnimatePresence>{showSplash && <SplashScreen onComplete={handleSplashComplete} />}</AnimatePresence><AmbientBackground><div className="film-grain" /><Navbar formData={locations.formData} /><main className="flex-1 w-full"><RegionalFeedbackPanel regional={{ ...regional, selectScenario: (id) => { setSelectedCrop(null); regional.selectScenario(id); }, updateParticipant: (id) => { setSelectedCrop(null); regional.updateParticipant(id); } }} result={advisory.result} quoteValid={quoteValid} onRefresh={regional.fetchAdvice} isFetching={advisory.isFetching} />{locations.isLoadingLocations && <p role="status" className={`max-w-5xl mx-auto mb-4 text-sm ${textSecondary}`}>Loading available historical locations…</p>}{locations.locationsError && <p role="alert" className="max-w-5xl mx-auto mb-4 text-sm text-rose-600 dark:text-rose-300">Location data unavailable: {locations.locationsError}</p>}{selectedCrop ? <><button type="button" onClick={() => setSelectedCrop(null)} className={`${glassClass} rounded-xl px-4 py-3 mb-5 mx-auto flex gap-2 items-center ${textPrimary}`}><ChevronLeft className="w-4 h-4" />Back to recommendations</button><ErrorBoundary title="Scenario calculations"><Suspense fallback={<p className={textSecondary}>Loading calculations…</p>}><AdvancedAnalytics crop={cropForAnalytics} area={locations.formData.area} /></Suspense></ErrorBoundary></> : <ErrorBoundary title="Regional advisory"><V2Dashboard formData={locations.formData} states={locations.states} districts={locations.districts} seasons={locations.seasons} onStateChange={(value) => changeLocation(locations.handleStateChange, value)} onDistrictChange={(value) => changeLocation(locations.handleDistrictChange, value)} onSeasonChange={(value) => changeLocation(locations.handleSeasonChange, value)} onAreaChange={(value) => { advisory.clearRecommendations(); locations.handleAreaChange(value); }} onFetch={regional.fetchAdvice} recommendations={advisory.recommendations} isFetching={advisory.isFetching} errorMessage={advisory.error} onViewAnalytics={setSelectedCrop} regional={regional.scenarioId ? regional : null} quoteValid={quoteValid} metadata={advisory.result} /></ErrorBoundary>}{regional.scenarioId && <ClassroomReplay />}</main></AmbientBackground></>;
}
export default function App() { return <ErrorBoundary title="AgriIntel"><ThemeProvider><AppContent /></ThemeProvider></ErrorBoundary>; }
