import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ShieldCheck, TrendingUp, AlertTriangle, Sprout, Sparkles, RefreshCw } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import RollingNumber from '../../components/common/RollingNumber';
import { playTactileClick } from '../../utils/audio';

export default function MonumentalCropSpecimen({
  crop,
  rank = 1,
  champion = null,
  formData = {},
  onSelectChampion,
  onViewAnalytics
}) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  // Interactive yield quantile simulation (10 to 90)
  const [simulatedQuantile, setSimulatedQuantile] = useState(50);

  if (!crop) return null;

  // Defensive accessors for all crop telemetry
  const q10 = Number(crop.Yield_q10 ?? 0);
  const q50 = Number(crop.Yield_q50 ?? 0);
  const q90 = Number(crop.Yield_q90 ?? 0);
  const baseExpectedProfit = Number(crop.Expected_Profit ?? 0);
  const var95 = Number(crop.Pessimistic_Profit ?? 0);
  const downsideRisk = Number(crop.Downside_Risk ?? 1);
  const safetyRating = crop.Safety_Rating || (var95 > 0 ? 'Safe' : 'Moderate Risk');
  const priceP50 = Number(crop.Price_p50 ?? 0);
  
  const agSharpe = downsideRisk > 0 ? (baseExpectedProfit / downsideRisk).toFixed(1) : '0.0';
  
  // Calculate simulated yield based on quantile slider
  let currentYield = q50;
  if (simulatedQuantile <= 50) {
    currentYield = q10 + ((simulatedQuantile - 10) / 40) * (q50 - q10);
  } else {
    currentYield = q50 + ((simulatedQuantile - 50) / 40) * (q90 - q50);
  }
  const yieldRatio = q50 > 0 ? (currentYield / q50) : 1;
  const simulatedProfit = Math.round(baseExpectedProfit * yieldRatio);

  const isChampion = rank === 1;
  const areaLabel = formData?.area ? Number(formData.area).toFixed(1) : '1.0';

  // Champion comparison calculations
  const championProfit = champion ? Number(champion.Expected_Profit ?? 0) : 0;
  const profitDelta = baseExpectedProfit - championProfit;
  const profitDeltaPercent = championProfit > 0 ? ((profitDelta / championProfit) * 100).toFixed(1) : '0.0';

  const handleSliderChange = (val) => {
    setSimulatedQuantile(Number(val));
    playTactileClick();
  };

  const handleResetMedian = () => {
    setSimulatedQuantile(50);
    playTactileClick();
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full max-w-5xl mx-auto ${glassClass} rounded-[2.5rem] p-8 sm:p-12 relative overflow-hidden shadow-2xl border border-white/20 dark:border-white/10 group backdrop-blur-2xl`}
    >
      {/* Specular Ambient Backlight */}
      <div className="absolute top-0 right-0 w-[550px] h-[550px] bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Main Specimen Grid */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-10 relative z-10">
        
        {/* Left Side: Monumental Title, Dynamic Rank & Interactive Uncertainty Ribbon */}
        <div className="flex-1 w-full">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={`flex items-center justify-center w-10 h-10 rounded-2xl font-mono-tech text-lg font-bold shadow-lg ${
              isChampion 
                ? 'bg-emerald-500 text-white shadow-emerald-500/30' 
                : 'bg-teal-600 text-white shadow-teal-600/30'
            }`}>
              #{rank}
            </span>
            <span className={`text-[11px] font-mono-tech uppercase tracking-widest font-semibold px-3 py-1.5 rounded-lg border ${
              isChampion
                ? 'text-emerald-600 dark:text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                : 'text-teal-600 dark:text-teal-400 border-teal-500/30 bg-teal-500/10'
            }`}>
              {isChampion ? 'PARETO OPTIMAL CHAMPION' : `ACTIVE SPECIMEN • CANDIDATE #${rank}`}
            </span>

            {/* Safety Rating Badge */}
            <span className={`text-[11px] font-mono-tech uppercase tracking-wider font-bold px-3 py-1.5 rounded-lg border ${
              safetyRating === 'Safe' 
                ? 'text-emerald-700 dark:text-emerald-300 border-emerald-500/20 bg-emerald-500/10' 
                : 'text-amber-700 dark:text-amber-300 border-amber-500/20 bg-amber-500/10'
            }`}>
              {safetyRating}
            </span>

            {/* If alternative candidate, quick button back to champion */}
            {!isChampion && champion && onSelectChampion && (
              <button
                type="button"
                onClick={onSelectChampion}
                className="text-[11px] font-mono-tech text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer ml-auto"
              >
                <span>&#8592; Back to Champion ({champion.Crop})</span>
              </button>
            )}
          </div>
          
          <h1 className={`text-6xl sm:text-7xl lg:text-[5.25rem] font-editorial font-bold ${textPrimary} tracking-tight leading-none mb-6`}>
            {crop.Crop}
          </h1>

          {/* Interactive Quantile Uncertainty Simulator Ribbon */}
          <div className="max-w-xl mt-8 p-5 rounded-3xl border border-black/5 dark:border-white/10 bg-black/5 dark:bg-white/5 backdrop-blur-md">
            <div className="flex items-center justify-between text-[11px] font-mono-tech mb-2.5 opacity-80 uppercase tracking-widest">
              <span className="flex items-center gap-1">
                <span>p10 (Pessimistic)</span>
              </span>
              <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold">
                <Sparkles className="w-3 h-3" />
                <span>Simulated Yield: {currentYield.toFixed(2)} t/ha</span>
                {simulatedQuantile !== 50 && (
                  <button
                    type="button"
                    onClick={handleResetMedian}
                    className="p-1 rounded-full hover:bg-emerald-500/20 text-emerald-500 cursor-pointer"
                    title="Reset to Median p50"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                )}
              </div>
              <span>p90 (Optimistic)</span>
            </div>
            
            {/* Interactive Slider Input */}
            <div className="relative mb-3">
              <input
                type="range"
                min="10"
                max="90"
                step="1"
                value={simulatedQuantile}
                onChange={(e) => handleSliderChange(e.target.value)}
                className="w-full h-3 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-emerald-600 via-teal-400 to-emerald-300 accent-emerald-600 shadow-sm"
              />
            </div>
            
            <div className="flex items-center justify-between text-xs sm:text-sm font-mono-tech font-bold">
              <span className="opacity-75">{q10.toFixed(1)} t/ha</span>
              <span className={`text-sm sm:text-base font-extrabold ${simulatedQuantile === 50 ? 'text-emerald-600 dark:text-emerald-400' : textPrimary}`}>
                p50: {q50.toFixed(1)} t/ha
              </span>
              <span className="opacity-75">{q90.toFixed(1)} t/ha</span>
            </div>
          </div>
        </div>

        {/* Right Side: Expected Profit & Deep Metrics */}
        <div className="flex flex-col items-start md:items-end w-full md:w-auto">
          <div className="mb-6 text-left md:text-right">
            <p className={`text-xs font-semibold uppercase tracking-widest mb-1.5 ${textSecondary}`}>
              Expected Net Profit ({areaLabel} HA)
            </p>
            <div className="text-5xl sm:text-6xl lg:text-7xl font-bold font-mono-tech text-emerald-600 dark:text-emerald-400 tabular-nums tracking-tight">
              <RollingNumber value={simulatedProfit} prefix="&#8377;" />
            </div>
            {simulatedQuantile !== 50 && (
              <p className="text-[11px] font-mono-tech text-emerald-600 dark:text-emerald-400 mt-1 font-semibold">
                Simulated at p{simulatedQuantile} percentile
              </p>
            )}
          </div>

          {/* Key Econometric Pills */}
          <div className="flex flex-wrap md:flex-col items-start md:items-end gap-2.5 font-mono-tech text-xs w-full sm:w-auto">
            {/* Ag-Sharpe */}
            <div className={`flex items-center justify-between md:justify-end gap-3 px-4 py-2 rounded-xl border w-full sm:w-auto ${
              darkMode ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-white/80 shadow-sm'
            }`}>
              <div className="flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                <span className={textSecondary}>AG-SHARPE:</span>
              </div>
              <span className={`font-bold ${textPrimary}`}>{agSharpe}x</span>
            </div>
            
            {/* VaR95 */}
            <div className={`flex items-center justify-between md:justify-end gap-3 px-4 py-2 rounded-xl border w-full sm:w-auto ${
              darkMode ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-white/80 shadow-sm'
            }`}>
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span className={textSecondary}>VaR95 FLOOR:</span>
              </div>
              <span className={`font-bold ${var95 >= 0 ? textPrimary : 'text-rose-500'}`}>
                &#8377;{Math.round(var95).toLocaleString('en-IN')}
              </span>
            </div>

            {/* Market Price Floor / Cost */}
            {priceP50 > 0 && (
              <div className={`flex items-center justify-between md:justify-end gap-3 px-4 py-2 rounded-xl border w-full sm:w-auto ${
                darkMode ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-white/80 shadow-sm'
              }`}>
                <div className="flex items-center gap-1.5">
                  <Sprout className="w-4 h-4 text-teal-500" />
                  <span className={textSecondary}>PRICE (p50):</span>
                </div>
                <span className={`font-bold ${textPrimary}`}>&#8377;{Math.round(priceP50).toLocaleString('en-IN')}/q</span>
              </div>
            )}

            {/* MSP Status */}
            <div className="flex items-center justify-between md:justify-end gap-2 px-4 py-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold w-full sm:w-auto">
              <ShieldCheck className="w-4 h-4" />
              <span>MSP ASSURED BENCHMARK</span>
            </div>
          </div>

          {/* Deep Analytics CTA */}
          <button
            id="inspect-analytics-btn"
            type="button"
            onClick={() => {
              if (onViewAnalytics) onViewAnalytics(crop);
            }}
            className="mt-8 group flex items-center gap-2.5 px-5 py-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-semibold text-sm transition-all duration-300 cursor-pointer shadow-md hover:shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Inspect Deep Economic Decomposition</span>
            <div className="p-1 rounded-full bg-emerald-500/20 group-hover:bg-emerald-500/30 transition-colors">
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </div>
          </button>
        </div>
      </div>

      {/* Head-to-Head Comparison Matrix (Visible when inspecting alternative candidate #2, #3, etc.) */}
      {!isChampion && champion && (
        <div className="mt-8 pt-6 border-t border-black/5 dark:border-white/10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/10 font-mono-tech text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">HEAD-TO-HEAD VS #1 {champion.Crop}:</span>
              <span className={profitDelta >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-500 font-bold'}>
                {profitDelta >= 0 ? `+₹${Math.round(profitDelta).toLocaleString('en-IN')}` : `-₹${Math.round(Math.abs(profitDelta)).toLocaleString('en-IN')}`} ({profitDeltaPercent}%)
              </span>
            </div>
            
            <div className="flex items-center gap-4 text-[11px] opacity-80">
              <span>Yield Δ: {(q50 - Number(champion.Yield_q50 ?? 0)).toFixed(1)} t/ha</span>
              <span>Price Δ: &#8377;{Math.round(priceP50 - Number(champion.Price_p50 ?? 0))}</span>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
