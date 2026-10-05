import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, TrendingUp } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0 },
};

export default function CandidateGallery({ candidates, onSelect, activeCrop }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="w-full max-w-5xl mx-auto mt-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-xs font-mono-tech font-bold uppercase tracking-widest ${textSecondary}`}>
          Alternative Frontier Candidates
        </h3>
        <span className={`text-[11px] font-mono-tech ${textSecondary}`}>
          Click candidate to inspect telemetry
        </span>
      </div>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        {candidates.map((crop, idx) => {
          const rank = idx + 2; // Since #1 is the champion
          const profit = Number(crop?.Expected_Profit ?? 0);
          const var95 = Number(crop?.Pessimistic_Profit ?? 0);
          const downsideRisk = Number(crop?.Downside_Risk ?? 1);
          const agSharpe = downsideRisk > 0 ? (profit / downsideRisk).toFixed(1) : '0.0';
          const safety = crop?.Safety_Rating || (var95 > 0 ? 'Safe' : 'Moderate Risk');
          const isSelected = activeCrop?.Crop === crop.Crop;

          return (
            <motion.button
              key={crop.Crop}
              variants={itemVariants}
              type="button"
              onClick={() => onSelect(crop)}
              className={`text-left p-5 rounded-2xl border transition-all duration-300 cursor-pointer group flex flex-col justify-between min-h-[160px] backdrop-blur-xl ${
                isSelected 
                  ? 'bg-emerald-500/15 border-emerald-500 shadow-xl ring-2 ring-emerald-500/40 -translate-y-1' 
                  : `${glassClass} border-white/20 dark:border-white/10 hover:border-emerald-500/50 hover:shadow-xl hover:-translate-y-1`
              }`}
            >
              <div className="flex items-center justify-between w-full mb-3">
                <div className="flex items-center gap-2">
                  <span className={`text-[11px] font-mono-tech font-bold px-2.5 py-0.5 rounded-lg shadow-sm ${
                    isSelected 
                      ? 'bg-emerald-500 text-white' 
                      : darkMode ? 'bg-white/10 text-slate-300' : 'bg-slate-200/80 text-slate-800'
                  }`}>
                    #{rank}
                  </span>
                  <span className={`text-[9px] font-mono-tech uppercase font-bold px-2 py-0.5 rounded ${
                    safety === 'Safe' 
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' 
                      : 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                  }`}>
                    {safety}
                  </span>
                </div>
                
                <div className={`p-1 rounded-full transition-colors ${
                  isSelected ? 'bg-emerald-500 text-white' : 'bg-black/5 dark:bg-white/5 text-slate-400 group-hover:text-emerald-500'
                }`}>
                  <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
              </div>

              <div>
                <h4 className={`text-2xl font-editorial font-bold leading-tight mb-3 ${textPrimary} tracking-tight`}>
                  {crop.Crop}
                </h4>
                
                <div className="space-y-1 text-xs font-mono-tech">
                  <div className="flex items-center justify-between">
                    <span className={textSecondary}>Exp. Profit:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      &#8377;{(profit / 1000).toFixed(1)}k
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className={textSecondary}>VaR Floor:</span>
                    <span className={`font-bold ${var95 >= 0 ? textPrimary : 'text-rose-500'}`}>
                      &#8377;{(var95 / 1000).toFixed(1)}k
                    </span>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-black/5 dark:border-white/10">
                    <span className={`flex items-center gap-1 text-[10px] ${textSecondary}`}>
                      <TrendingUp className="w-3 h-3 text-emerald-500" />
                      Sharpe:
                    </span>
                    <span className={`font-semibold ${textPrimary}`}>
                      {agSharpe}x
                    </span>
                  </div>
                </div>
              </div>
            </motion.button>
          );
        })}
      </motion.div>
    </div>
  );
}
