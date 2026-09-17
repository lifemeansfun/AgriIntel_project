import React from 'react';
import {
  Calendar,
  Loader2,
  CloudRain,
  Sun,
  Minus,
  Plus,
  Compass,
  Sparkles,
} from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import FormSelect from '../../components/common/FormSelect';

const QUICK_DISTRICTS = ['Agar Malwa', 'Indore', 'Ujjain', 'Dewas', 'Bhopal'];

export default function LocationFilterForm({
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit && !isFetching && formData.season) {
      onSubmit();
    }
  };

  const areaValue = parseFloat(formData.area) || 1.0;
  const acres = (areaValue * 2.47105).toFixed(2);
  const bighas = (areaValue * 3.95368).toFixed(2);

  const adjustArea = (delta) => {
    const next = Math.max(0.1, Math.min(50, parseFloat((areaValue + delta).toFixed(1))));
    onAreaChange(String(next));
  };

  const handleQuickDistrict = (distName) => {
    if (districts.includes(distName)) {
      onDistrictChange(distName);
    }
  };

  return (
    <div className={`${glassClass} rounded-2xl p-6 lg:p-8 relative overflow-hidden`}>
      {/* Agro-Climatic Telemetry Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-black/5 dark:border-white/10">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h2 className={`text-lg font-bold ${textPrimary} leading-tight`}>
              Location &amp; Land
            </h2>
            <span className="text-[10px] font-mono-tech tracking-wider uppercase opacity-60">
              FIELD INSTRUMENT &bull; LAT 23.7&deg;N
            </span>
          </div>
        </div>

        <span className="text-[10px] font-mono-tech px-2.5 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
          AGRO-CLIMATIC VIII
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <FormSelect
          id="select-state"
          label="State Jurisdiction"
          value={formData.state}
          onChange={(e) => onStateChange(e.target.value)}
          options={states}
          placeholder="Select State"
        />

        <div className="space-y-1.5">
          <FormSelect
            id="select-district"
            label="District Observation Hub"
            value={formData.district}
            onChange={(e) => onDistrictChange(e.target.value)}
            options={districts}
            placeholder="Select District"
            disabled={!formData.state || districts.length === 0}
          />

          {/* Quick-select District Chips */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[10px] uppercase font-mono-tech opacity-60 mr-1">Presets:</span>
            {QUICK_DISTRICTS.map((name) => {
              const isSelected = formData.district === name;
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => handleQuickDistrict(name)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-mono-tech transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                      : darkMode
                      ? 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200'
                  }`}
                >
                  {name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tactile Seasonal Dial / Segments */}
        <div className="space-y-2">
          <label className={`block text-xs font-semibold uppercase tracking-wider ${textSecondary}`}>
            Crop Season Cycle
          </label>
          <div className="grid grid-cols-3 gap-2 p-1.5 rounded-2xl bg-black/5 dark:bg-black/25 border border-emerald-500/15">
            {seasons.map((season) => {
              const isSelected = formData.season === season;
              const isKharif = season.toLowerCase().includes('kharif');
              const isRabi = season.toLowerCase().includes('rabi');
              const Icon = isKharif ? CloudRain : isRabi ? Sun : Calendar;

              return (
                <button
                  key={season}
                  type="button"
                  onClick={() => onSeasonChange(season)}
                  className={`relative p-2.5 rounded-xl flex flex-col items-center justify-center gap-1.5 transition-all text-center cursor-pointer select-none ${
                    isSelected
                      ? darkMode
                        ? 'bg-emerald-600 text-white shadow-md'
                        : 'bg-white text-emerald-950 shadow-md border border-emerald-500/20'
                      : darkMode
                      ? 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isSelected ? 'text-white dark:text-white' : 'opacity-70'}`} />
                  <span className="text-xs font-semibold leading-none">{season}</span>
                  <span className="text-[9px] font-mono-tech opacity-60 leading-none">
                    {isKharif ? 'Monsoon' : isRabi ? 'Winter' : 'Annual'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Precision Land Area Instrument */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <label htmlFor="range-land-area" className={`text-xs font-semibold uppercase tracking-wider ${textSecondary}`}>
              Land Holding Area
            </label>
            <div className="font-mono-tech text-xs font-bold text-emerald-600 dark:text-emerald-400">
              {areaValue.toFixed(1)} HA
            </div>
          </div>

          {/* Stepper + Digital Readout */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => adjustArea(-0.5)}
              className={`p-2.5 rounded-xl border transition-colors cursor-pointer ${
                darkMode
                  ? 'bg-slate-800/80 border-white/10 hover:bg-slate-700 text-slate-200'
                  : 'bg-slate-100 border-slate-200 hover:bg-slate-200 text-slate-700'
              }`}
              aria-label="Decrease area by 0.5 hectares"
            >
              <Minus className="w-4 h-4" />
            </button>

            <input
              id="input-land-area"
              type="number"
              step="0.1"
              min="0.1"
              max="50"
              value={formData.area}
              onChange={(e) => onAreaChange(e.target.value)}
              className={`flex-1 text-center font-mono-tech font-bold text-lg border rounded-xl py-2 px-3 focus:outline-none focus:ring-2 transition-colors ${inputClass}`}
            />

            <button
              type="button"
              onClick={() => adjustArea(0.5)}
              className={`p-2.5 rounded-xl border transition-colors cursor-pointer ${
                darkMode
                  ? 'bg-slate-800/80 border-white/10 hover:bg-slate-700 text-slate-200'
                  : 'bg-slate-100 border-slate-200 hover:bg-slate-200 text-slate-700'
              }`}
              aria-label="Increase area by 0.5 hectares"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Smooth Range Slider */}
          <input
            id="range-land-area"
            type="range"
            min="0.5"
            max="20"
            step="0.5"
            value={areaValue}
            onChange={(e) => onAreaChange(e.target.value)}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-emerald-950/20 dark:bg-emerald-500/20 accent-emerald-600"
          />

          {/* Live Unit Conversion Telemetry */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 font-mono-tech text-[11px] text-emerald-700 dark:text-emerald-300">
            <span>EQUIVALENT LAND:</span>
            <span className="font-bold">
              {acres} ACRES <span className="opacity-40">|</span> {bighas} BIGHAS
            </span>
          </div>
        </div>

        {/* Tactile Optimization Trigger Button */}
        <button
          type="submit"
          id="btn-get-recommendations"
          disabled={isFetching || !formData.season}
          className="w-full mt-2 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-2xl transition-all duration-200 shadow-xl hover:shadow-emerald-900/40 flex justify-center items-center gap-2.5 cursor-pointer"
        >
          {isFetching ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="font-mono-tech tracking-wide">COMPUTING RISK FRONTIER...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-emerald-200" />
              <span className="tracking-wide">Run Advisory Optimization</span>
              <span className="text-[10px] font-mono-tech px-1.5 py-0.5 rounded bg-white/20 text-emerald-100">
                &lambda;=0.5
              </span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
