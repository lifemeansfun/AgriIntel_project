import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0 },
};

export default function CandidateGallery({ candidates, onSelect, activeCrop }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="w-full max-w-5xl mx-auto mt-6">
      <h3 className={`text-sm font-semibold uppercase tracking-widest mb-4 ${textSecondary}`}>
        Alternative Candidates
      </h3>
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
          const isSelected = activeCrop?.Crop === crop.Crop;

          return (
            <motion.button
              key={crop.Crop}
              variants={itemVariants}
              onClick={() => onSelect(crop)}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group flex flex-col justify-between min-h-[140px] ${
                isSelected 
                  ? 'bg-emerald-500/10 border-emerald-500 shadow-md ring-1 ring-emerald-500' 
                  : `${glassClass} hover:border-emerald-500/50 hover:shadow-lg hover:-translate-y-0.5`
              }`}
            >
              <div className="flex items-center justify-between w-full mb-3">
                <span className={`text-[10px] font-mono-tech font-bold px-2 py-0.5 rounded-md ${
                  isSelected ? 'bg-emerald-500 text-white' : darkMode ? 'bg-white/10' : 'bg-slate-100'
                }`}>
                  #{rank}
                </span>
                <ArrowUpRight className={`w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 ${
                  isSelected ? 'text-emerald-500' : 'text-slate-400 group-hover:text-emerald-500'
                }`} />
              </div>

              <div>
                <h4 className={`text-xl font-editorial font-bold leading-tight mb-2 ${textPrimary}`}>
                  {crop.Crop}
                </h4>
                <div className="flex items-center justify-between text-xs font-mono-tech">
                  <span className={textSecondary}>Exp: <span className="font-bold text-emerald-600 dark:text-emerald-400">&#8377;{(profit/1000).toFixed(1)}k</span></span>
                  <span className={textSecondary}>VaR: <span className={`font-bold ${var95 >= 0 ? textPrimary : 'text-rose-500'}`}>&#8377;{(var95/1000).toFixed(1)}k</span></span>
                </div>
              </div>
            </motion.button>
          );
        })}
      </motion.div>
    </div>
  );
}
