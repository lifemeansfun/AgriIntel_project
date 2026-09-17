import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ShieldCheck, TrendingUp, AlertTriangle } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import RollingNumber from '../../components/common/RollingNumber';

export default function MonumentalCropSpecimen({ crop, onViewAnalytics }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  if (!crop) return null;

  // Defensive accessors for all crop data
  const q10 = Number(crop.Yield_q10 ?? 0);
  const q50 = Number(crop.Yield_q50 ?? 0);
  const q90 = Number(crop.Yield_q90 ?? 0);
  const expectedProfit = Number(crop.Expected_Profit ?? 0);
  const var95 = Number(crop.Pessimistic_Profit ?? 0);
  const downsideRisk = Number(crop.Downside_Risk ?? 1);
  
  const agSharpe = downsideRisk > 0 ? (expectedProfit / downsideRisk).toFixed(1) : '0.0';
  
  const yieldRange = Math.max(0.01, q90 - q10);
  const medianPinPercent = Math.min(92, Math.max(8, ((q50 - q10) / yieldRange) * 100));

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full max-w-5xl mx-auto ${glassClass} rounded-[2rem] p-8 sm:p-12 relative overflow-hidden shadow-2xl group`}
    >
      {/* Specular Ambient Backlight */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent pointer-events-none" />

      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-10 relative z-10">
        
        {/* Left Side: Monumental Title & Rank */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-4">
            <span className="flex items-center justify-center w-10 h-10 rounded-2xl bg-emerald-500 text-white font-mono-tech text-lg font-bold shadow-lg shadow-emerald-500/30">
              #1
            </span>
            <span className="text-[11px] font-mono-tech uppercase tracking-widest text-emerald-600 dark:text-emerald-400 font-semibold px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10">
              PARETO OPTIMAL CHAMPION
            </span>
          </div>
          
          <h1 className={`text-6xl sm:text-7xl lg:text-[5rem] font-editorial font-bold ${textPrimary} tracking-tighter leading-none mb-6`}>
            {crop.Crop}
          </h1>

          {/* Quantile Uncertainty Ribbon */}
          <div className="max-w-md mt-8">
            <div className="flex items-center justify-between text-[11px] font-mono-tech mb-2 opacity-70 uppercase tracking-widest">
              <span>p10 (Pessimistic)</span>
              <span>Yield Distribution</span>
              <span>p90 (Optimistic)</span>
            </div>
            
            <div className="relative h-2 rounded-full bg-emerald-950/10 dark:bg-emerald-500/20 mb-2">
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-emerald-600/80 via-emerald-400 to-teal-300 opacity-90" />
              {/* Median Marker */}
              <div
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white shadow-md border-2 border-emerald-600 z-20 transition-all duration-500"
                style={{ left: `${medianPinPercent}%`, transform: 'translate(-50%, -50%)' }}
              />
            </div>
            
            <div className="flex items-center justify-between text-sm font-mono-tech font-bold">
              <span>{q10.toFixed(1)} t/ha</span>
              <span className="text-emerald-600 dark:text-emerald-400">{q50.toFixed(1)} t/ha</span>
              <span>{q90.toFixed(1)} t/ha</span>
            </div>
          </div>
        </div>

        {/* Right Side: Expected Profit & Deep Metrics */}
        <div className="flex flex-col items-start md:items-end w-full md:w-auto">
          <div className="mb-8 text-left md:text-right">
            <p className={`text-sm font-semibold uppercase tracking-widest mb-2 ${textSecondary}`}>
              Expected Profit
            </p>
            <div className="text-5xl sm:text-6xl font-bold font-mono-tech text-emerald-600 dark:text-emerald-400 tabular-nums tracking-tight">
              <RollingNumber value={expectedProfit} prefix="&#8377;" />
            </div>
          </div>

          <div className="flex flex-wrap md:flex-col items-center md:items-end gap-3 font-mono-tech text-xs">
            {/* Ag-Sharpe */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${darkMode ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-slate-50'}`}>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <span className={textSecondary}>AG-SHARPE:</span>
              <span className={`font-bold ${textPrimary}`}>{agSharpe}x</span>
            </div>
            
            {/* VaR95 */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${darkMode ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-slate-50'}`}>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span className={textSecondary}>VaR95 FLOOR:</span>
              <span className={`font-bold ${var95 >= 0 ? textPrimary : 'text-rose-500'}`}>
                &#8377;{Math.round(var95).toLocaleString('en-IN')}
              </span>
            </div>

            {/* MSP Status */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>MSP ACTIVE</span>
            </div>
          </div>

          {/* Deep Analytics CTA */}
          <button
            onClick={() => onViewAnalytics(crop)}
            className="mt-8 group flex items-center gap-2 text-sm font-semibold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors cursor-pointer"
          >
            <span>Inspect Deep Economic Decomposition</span>
            <div className="p-1.5 rounded-full bg-emerald-500/10 group-hover:bg-emerald-500/20 transition-colors">
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </div>
          </button>
        </div>
      </div>
    </motion.div>
  );
}
