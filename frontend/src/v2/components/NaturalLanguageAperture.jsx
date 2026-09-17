import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Sliders, MapPin, Calendar, Sparkles, Loader2, X, Plus, Minus } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

export default function NaturalLanguageAperture({
  formData,
  states = [],
  districts = [],
  seasons = [],
  onStateChange,
  onDistrictChange,
  onSeasonChange,
  onAreaChange,
  onSubmit,
  isFetching = false,
}) {
  const { glassClass, darkMode, textPrimary, textSecondary, inputClass } = useTheme();
  
  // popover state: 'none' | 'area' | 'location' | 'season'
  const [activePopover, setActivePopover] = useState('none');
  const containerRef = useRef(null);

  // Close popover on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setActivePopover('none');
      }
    };
    const handleEscape = (e) => {
      if (e.key === 'Escape') setActivePopover('none');
    };

    if (activePopover !== 'none') {
      window.addEventListener('pointerdown', handleOutsideClick, { passive: true });
      window.addEventListener('keydown', handleEscape, { passive: true });
    }

    return () => {
      window.removeEventListener('pointerdown', handleOutsideClick);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [activePopover]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit && !isFetching && formData.season && formData.state && formData.district) {
      onSubmit();
      setActivePopover('none');
    }
  };

  const handleQuickDistrict = (distName) => {
    if (districts.includes(distName)) {
      onDistrictChange(distName);
    }
  };

  const areaValue = parseFloat(formData.area) || 1.0;
  const adjustArea = (delta) => {
    const next = Math.max(0.1, Math.min(50, parseFloat((areaValue + delta).toFixed(1))));
    onAreaChange(String(next));
  };

  const QUICK_DISTRICTS = ['Agar Malwa', 'Indore', 'Ujjain', 'Dewas', 'Bhopal'];

  return (
    <div className="relative w-full max-w-5xl mx-auto mb-12 z-40" ref={containerRef}>
      <form onSubmit={handleSubmit} className={`${glassClass} rounded-2xl p-4 sm:p-5 flex flex-col md:flex-row items-center justify-between gap-4 sm:gap-6 shadow-xl`}>
        {/* Editorial Command Sentence */}
        <div className={`text-base sm:text-lg lg:text-xl font-editorial ${textPrimary} flex-1 leading-loose text-center md:text-left flex flex-wrap items-center justify-center md:justify-start gap-x-2 gap-y-3`}>
          <span>Advising on</span>
          
          {/* Area Token */}
          <button 
            type="button"
            onClick={() => setActivePopover(activePopover === 'area' ? 'none' : 'area')}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border font-mono-tech text-sm transition-all cursor-pointer ${
              activePopover === 'area' 
                ? 'bg-emerald-500/20 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-inner' 
                : `${darkMode ? 'bg-black/30 border-white/10 hover:border-emerald-500/50' : 'bg-white/60 border-slate-200 hover:border-emerald-500/50'}`
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span className="font-bold">{areaValue.toFixed(1)} HA</span>
            <ChevronDown className={`w-3 h-3 transition-transform ${activePopover === 'area' ? 'rotate-180' : ''}`} />
          </button>

          <span>in</span>

          {/* Location Token */}
          <button 
            type="button"
            onClick={() => setActivePopover(activePopover === 'location' ? 'none' : 'location')}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border font-sans text-sm font-semibold transition-all cursor-pointer ${
              activePopover === 'location' 
                ? 'bg-emerald-500/20 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-inner' 
                : `${darkMode ? 'bg-black/30 border-white/10 hover:border-emerald-500/50' : 'bg-white/60 border-slate-200 hover:border-emerald-500/50'}`
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>{formData.district || 'Select District'}</span>
            {formData.state && <span className="opacity-60 hidden sm:inline">, {formData.state}</span>}
            <ChevronDown className={`w-3 h-3 transition-transform ${activePopover === 'location' ? 'rotate-180' : ''}`} />
          </button>

          <span>for</span>

          {/* Season Token */}
          <button 
            type="button"
            onClick={() => setActivePopover(activePopover === 'season' ? 'none' : 'season')}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border font-sans text-sm font-semibold transition-all cursor-pointer ${
              activePopover === 'season' 
                ? 'bg-emerald-500/20 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-inner' 
                : `${darkMode ? 'bg-black/30 border-white/10 hover:border-emerald-500/50' : 'bg-white/60 border-slate-200 hover:border-emerald-500/50'}`
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>{formData.season || 'Select Season'}</span>
            <ChevronDown className={`w-3 h-3 transition-transform ${activePopover === 'season' ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* Compute Action Button */}
        <button
          type="submit"
          disabled={isFetching || !formData.season || !formData.district}
          className="shrink-0 w-full md:w-auto bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-emerald-900/40 flex justify-center items-center gap-2 cursor-pointer"
        >
          {isFetching ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="font-mono-tech text-sm tracking-wide">COMPUTING...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-emerald-200" />
              <span className="text-sm">Compute Frontier</span>
            </>
          )}
        </button>
      </form>

      {/* Floating Popovers */}
      {activePopover !== 'none' && (
        <div className={`absolute top-full left-0 right-0 md:left-auto md:right-auto md:w-[420px] mt-4 p-5 rounded-2xl shadow-2xl border transition-all animate-in fade-in slide-in-from-top-2 ${
          darkMode ? 'bg-slate-900/95 border-white/15' : 'bg-white/95 border-slate-200'
        } backdrop-blur-xl z-50`}
        >
          {/* Close Button */}
          <button 
            type="button" 
            onClick={() => setActivePopover('none')}
            className={`absolute top-4 right-4 p-1.5 rounded-full transition-colors cursor-pointer ${
              darkMode ? 'hover:bg-white/10 text-slate-400' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <X className="w-4 h-4" />
          </button>

          {activePopover === 'area' && (
            <div className="space-y-5 pt-2">
              <h3 className={`text-sm font-bold uppercase tracking-wider ${textSecondary}`}>Adjust Land Area</h3>
              
              <div className="flex items-center gap-3">
                <button type="button" onClick={() => adjustArea(-0.5)} className={`p-3 rounded-xl border transition-colors cursor-pointer ${darkMode ? 'bg-slate-800/80 border-white/10 hover:bg-slate-700 text-slate-200' : 'bg-slate-100 border-slate-200 hover:bg-slate-200 text-slate-700'}`}>
                  <Minus className="w-4 h-4" />
                </button>
                <input
                  type="number" step="0.1" min="0.1" max="50"
                  value={formData.area}
                  onChange={(e) => onAreaChange(e.target.value)}
                  className={`flex-1 text-center font-mono-tech font-bold text-2xl border rounded-xl py-2 px-3 focus:outline-none focus:ring-2 transition-colors ${inputClass}`}
                />
                <button type="button" onClick={() => adjustArea(0.5)} className={`p-3 rounded-xl border transition-colors cursor-pointer ${darkMode ? 'bg-slate-800/80 border-white/10 hover:bg-slate-700 text-slate-200' : 'bg-slate-100 border-slate-200 hover:bg-slate-200 text-slate-700'}`}>
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              <input
                type="range" min="0.5" max="20" step="0.5"
                value={areaValue}
                onChange={(e) => onAreaChange(e.target.value)}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-emerald-950/20 dark:bg-emerald-500/20 accent-emerald-600"
              />

              <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 font-mono-tech text-xs text-emerald-700 dark:text-emerald-300">
                <span>EQUIVALENT:</span>
                <span className="font-bold">{(areaValue * 2.47105).toFixed(2)} ACRES | {(areaValue * 3.95368).toFixed(2)} BIGHAS</span>
              </div>
            </div>
          )}

          {activePopover === 'location' && (
            <div className="space-y-4 pt-2">
              <h3 className={`text-sm font-bold uppercase tracking-wider ${textSecondary}`}>Select Location</h3>
              
              <div className="space-y-3">
                <select
                  value={formData.state}
                  onChange={(e) => onStateChange(e.target.value)}
                  className={`w-full text-sm border rounded-xl py-2.5 px-3 focus:outline-none focus:ring-2 transition-colors ${inputClass}`}
                >
                  <option value="">Select State...</option>
                  {states.map(s => <option key={s} value={s}>{s}</option>)}
                </select>

                <select
                  value={formData.district}
                  onChange={(e) => onDistrictChange(e.target.value)}
                  disabled={!formData.state || districts.length === 0}
                  className={`w-full text-sm border rounded-xl py-2.5 px-3 focus:outline-none focus:ring-2 transition-colors ${inputClass}`}
                >
                  <option value="">Select District...</option>
                  {districts.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>

              <div className="pt-2">
                <p className={`text-[10px] uppercase font-mono-tech mb-2 ${textSecondary}`}>Quick Presets:</p>
                <div className="flex flex-wrap gap-2">
                  {QUICK_DISTRICTS.map((name) => (
                    <button
                      key={name} type="button"
                      onClick={() => handleQuickDistrict(name)}
                      className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
                        formData.district === name
                          ? 'bg-emerald-600 text-white shadow-sm'
                          : darkMode ? 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10' : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200'
                      }`}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activePopover === 'season' && (
            <div className="space-y-4 pt-2">
              <h3 className={`text-sm font-bold uppercase tracking-wider ${textSecondary}`}>Crop Season Cycle</h3>
              <div className="grid grid-cols-1 gap-2">
                {seasons.map((season) => {
                  const isSelected = formData.season === season;
                  return (
                    <button
                      key={season} type="button"
                      onClick={() => {
                        onSeasonChange(season);
                        setActivePopover('none');
                      }}
                      className={`p-3 rounded-xl flex items-center justify-between transition-all cursor-pointer ${
                        isSelected
                          ? darkMode ? 'bg-emerald-600/20 border-emerald-500 text-emerald-400 border' : 'bg-emerald-50 border-emerald-500 text-emerald-700 border'
                          : darkMode ? 'bg-black/20 hover:bg-white/5 text-slate-300 border border-transparent' : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border border-transparent'
                      }`}
                    >
                      <span className="font-semibold text-sm">{season}</span>
                      {isSelected && <Sparkles className="w-4 h-4" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
