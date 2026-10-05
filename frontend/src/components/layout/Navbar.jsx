import React, { useState } from 'react';
import { Leaf, Moon, Sun, Radio, Volume2, VolumeX } from '../common/Icons';
import { useTheme } from '../../context/useTheme';
import { toggleAmbientSoundscape, playTactileClick } from '../../utils/audio';

const DISTRICT_COORDINATES = {
  'Agar Malwa': '23.7°N, 76.0°E',
  'Indore': '22.7°N, 75.8°E',
  'Bhopal': '23.2°N, 77.4°E',
  'Ujjain': '23.1°N, 75.7°E',
  'Dewas': '22.9°N, 76.0°E',
  'Pune': '18.5°N, 73.8°E',
  'Nashik': '19.9°N, 73.7°E',
  'Nagpur': '21.1°N, 79.0°E',
  'Aurangabad': '19.8°N, 75.3°E',
  'Ahmednagar': '19.0°N, 74.7°E',
  'Amritsar': '31.6°N, 74.8°E',
  'Ludhiana': '30.9°N, 75.8°E',
  'Jalandhar': '31.3°N, 75.5°E',
  'Patiala': '30.3°N, 76.4°E',
  'Bathinda': '30.2°N, 74.9°E',
  'Chennai': '13.0°N, 80.2°E',
  'Coimbatore': '11.0°N, 76.9°E',
  'Madurai': '9.9°N, 78.1°E',
  'Tiruchirappalli': '10.7°N, 78.7°E',
  'Salem': '11.6°N, 78.1°E',
  'Lucknow': '26.8°N, 80.9°E',
  'Kanpur': '26.4°N, 80.3°E',
  'Agra': '27.1°N, 78.0°E',
  'Varanasi': '25.3°N, 82.9°E',
  'Meerut': '28.9°N, 77.7°E'
};

export default function Navbar({ uiVersion = 'v1', setUiVersion, formData = {} }) {
  const { darkMode, toggleDarkMode, glassClass, textPrimary } = useTheme();
  const [isAudioOn, setIsAudioOn] = useState(false);

  const currentDistrict = formData?.district || 'Agar Malwa';
  const coords = DISTRICT_COORDINATES[currentDistrict] || '23.7°N, 76.0°E';

  const handleAudioToggle = () => {
    const nextState = !isAudioOn;
    setIsAudioOn(nextState);
    toggleAmbientSoundscape(nextState);
  };

  const handleVersionChange = (version) => {
    playTactileClick();
    setUiVersion(version);
  };

  const handleThemeChange = () => {
    playTactileClick();
    toggleDarkMode();
  };

  return (
    <header className={`${glassClass} rounded-2xl px-5 py-3.5 flex justify-between items-center mb-8 relative z-20 shadow-xl border border-white/20 dark:border-white/10 backdrop-blur-2xl`}>
      {/* Left: Brand Identity */}
      <div className="flex items-center gap-3.5">
        <div className={`p-2.5 rounded-xl border shadow-sm ${
          darkMode
            ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-400 shadow-emerald-950/50'
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700'
        }`}>
          <Leaf className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className={`text-2xl font-editorial font-bold tracking-tight leading-none ${textPrimary}`}>
              AgriIntel
            </h1>
            <span className="text-[10px] font-mono-tech font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              v4.2
            </span>
          </div>
          <p className="text-[9px] font-mono-tech tracking-widest uppercase font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
            FRONTIER AGRICULTURAL INTELLIGENCE
          </p>
        </div>
      </div>

      {/* Center: Dual Version Switcher */}
      <div className="hidden lg:flex items-center p-1 rounded-xl border bg-black/5 dark:bg-white/5 font-mono-tech text-xs font-semibold shadow-inner">
        <button
          type="button"
          onClick={() => handleVersionChange('v1')}
          className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${
            uiVersion === 'v1'
              ? darkMode
                ? 'bg-slate-700 text-white shadow-md'
                : 'bg-white text-emerald-950 shadow-md border border-slate-200'
              : darkMode
              ? 'text-slate-400 hover:text-white'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          V1 Cockpit
        </button>
        <button
          type="button"
          onClick={() => handleVersionChange('v2')}
          className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${
            uiVersion === 'v2'
              ? darkMode
                ? 'bg-emerald-600 text-white shadow-md'
                : 'bg-emerald-600 text-white shadow-md border border-emerald-500/20'
              : darkMode
              ? 'text-slate-400 hover:text-white'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          V2 Monograph
        </button>
      </div>

      {/* Right: Soundscape, GPS Satellite Coordinates & Celestial Theme Toggle */}
      <div className="flex items-center gap-3">
        {/* Dynamic Satellite Coordinates */}
        <div className="hidden sm:flex items-center gap-1.5 font-mono-tech text-[10.5px] text-emerald-600/90 dark:text-emerald-400/90 px-2.5 py-1 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
          <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-500" />
          <span>{coords}</span>
        </div>

        {/* Ambient Soundscape Toggle */}
        <button
          type="button"
          id="soundscape-toggle-btn"
          onClick={handleAudioToggle}
          className={`flex items-center gap-1.5 p-2 rounded-xl border transition-all cursor-pointer ${
            isAudioOn
              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-600 dark:text-emerald-400 shadow-sm'
              : darkMode
              ? 'bg-slate-900/60 border-white/10 text-slate-400 hover:text-slate-200'
              : 'bg-white/80 border-slate-200 text-slate-500 hover:text-slate-800 shadow-sm'
          }`}
          aria-label={isAudioOn ? 'Mute Ambient Field Soundscape' : 'Enable Ambient Field Soundscape'}
          title={isAudioOn ? 'Soundscape Active • Click to Mute' : 'Enable Tactile & Atmospheric Audio'}
        >
          {isAudioOn ? <Volume2 className="w-4 h-4 animate-bounce" /> : <VolumeX className="w-4 h-4" />}
          <span className="text-[10px] font-mono-tech font-bold hidden md:inline">
            {isAudioOn ? 'AUDIO ON' : 'AUDIO'}
          </span>
        </button>

        {/* Theme Switcher */}
        <button
          type="button"
          onClick={handleThemeChange}
          className={`flex items-center gap-2 p-1.5 px-3 rounded-full border transition-all cursor-pointer ${
            darkMode
              ? 'bg-slate-900/80 border-white/15 text-amber-300 hover:bg-slate-800'
              : 'bg-white/80 border-slate-200 text-slate-700 hover:bg-slate-100 shadow-sm'
          }`}
          aria-label="Toggle Celestial Day/Night Theme"
          title={darkMode ? 'Switch to Sunlight Day Mode' : 'Switch to Midnight Starry Mode'}
        >
          {darkMode ? (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span className="text-[11px] font-mono-tech font-semibold">NIGHT</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-slate-600" />
              <span className="text-[11px] font-mono-tech font-semibold">DAY</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
