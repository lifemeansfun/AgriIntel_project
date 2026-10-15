import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, RefreshCw } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import { interpolateYield, scenarioProfit, formatMoney, formatQuantity } from '../../services/scenarios';

export default function MonumentalCropSpecimen({ crop, rank = 1, formData = {}, onViewAnalytics, feedback, quoteValid, onCommit, busy }) {
  const { glassClass, textPrimary, textSecondary } = useTheme();
  const [position, setPosition] = useState(50);
  if (!crop) return null;
  const currentYield = interpolateYield(crop, position);
  const profit = scenarioProfit(currentYield, crop.Price_central, crop.Cost_per_ha, formData.area);
  return (
    <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className={`${glassClass} w-full max-w-5xl mx-auto rounded-[2.5rem] p-6 sm:p-10 shadow-2xl ${textPrimary}`} aria-label={`${crop.Crop} recommendation`}>
      <div className="flex flex-col lg:flex-row gap-8 lg:gap-12 justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-mono-tech uppercase tracking-widest text-emerald-700 dark:text-emerald-300 mb-4">Rank {rank} · scenario score {formatMoney(crop.Score)}</p>
          <h2 className="font-editorial font-bold text-5xl sm:text-7xl break-words">{crop.Crop}</h2>
          <p className={`mt-3 text-sm ${textSecondary}`}>Yield estimates for the historical selection · tonnes per hectare</p>
          <div className="grid grid-cols-3 gap-3 mt-6 text-center font-mono-tech">
            {[['Lower q10', crop.Yield_q10], ['Median q50', crop.Yield_q50], ['Upper q90', crop.Yield_q90]].map(([label, value]) => <div key={label} className="p-3 rounded-xl bg-emerald-500/10"><span className={`block text-xs ${textSecondary}`}>{label}</span><strong className="block mt-2 text-lg">{formatQuantity(value, 2)}</strong></div>)}
          </div>
          <div className="mt-6 p-4 border border-emerald-500/20 rounded-2xl">
            <label htmlFor="yield-scenario-slider" className="block text-sm font-semibold">Explore an interpolated yield scenario</label>
            <input id="yield-scenario-slider" aria-label="Interpolated yield scenario" type="range" min="10" max="90" value={position} disabled={currentYield === null} onChange={(event) => setPosition(Number(event.target.value))} className="w-full mt-4 accent-emerald-600" />
            <div className="flex flex-wrap justify-between gap-2 text-sm mt-2"><span>{formatQuantity(currentYield, 2)} t/ha at the central scenario price</span><button type="button" onClick={() => setPosition(50)} className="flex items-center gap-1 text-emerald-700 dark:text-emerald-300"><RefreshCw className="w-3 h-3" />Reset median</button></div>
            <p className={`text-xs mt-3 leading-relaxed ${textSecondary}`}>Intermediate positions are linear illustrations, not additional calibrated quantiles. Price and cultivation cost stay fixed.</p>
          </div>
        </div>
        <div className="lg:w-80 shrink-0">
          <p className={`text-xs uppercase tracking-wider ${textSecondary}`}>{position === 50 ? 'Central scenario profit' : 'Interpolated scenario profit'} · {formatQuantity(formData.area)} ha</p>
          <p className="font-mono-tech font-bold text-4xl sm:text-5xl text-emerald-700 dark:text-emerald-300 mt-2 break-words">{formatMoney(profit)}</p>
          <p className={`text-xs mt-2 mb-5 ${textSecondary}`}>All money in 2011-base rupees · modeled scenarios</p>
          <dl className="space-y-3 text-sm">
            {[['Pessimistic profit', formatMoney(crop.Pessimistic_Profit)], ['Downside gap', formatMoney(crop.Downside_Gap)], ['Central price / quintal', formatMoney(crop.Price_central)], ['Cultivation cost / hectare', formatMoney(crop.Cost_per_ha)]].map(([label, value]) => <div key={label} className="flex justify-between gap-3 border-b border-emerald-500/15 pb-3"><dt className={textSecondary}>{label}</dt><dd className="font-mono-tech text-right">{value}</dd></div>)}
          </dl>
          {feedback && <div className="mt-5"><button type="button" onClick={() => onCommit(crop.Crop)} disabled={busy || !crop.Eligible || !quoteValid || feedback.state?.commitment || !feedback.state || feedback.stateError} className="w-full rounded-xl px-4 py-3 bg-emerald-700 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed">{busy ? 'Saving commitment…' : 'Commit planting'}</button><p className={`text-xs leading-relaxed mt-2 ${textSecondary}`}>{feedback.state?.commitment ? 'Cancel your active commitment before choosing another crop.' : !crop.Eligible ? crop.Ineligibility_Reason || 'This crop is unavailable for the requested area.' : !quoteValid ? 'Refresh recommendations for a current quote.' : 'A commitment updates shared capacity. Exploring this page reserves nothing.'}</p></div>}
          <button id="inspect-analytics-btn" type="button" onClick={() => onViewAnalytics?.(crop)} className="mt-5 text-emerald-700 dark:text-emerald-300 font-semibold flex items-center gap-2 text-sm">Inspect scenario calculations<ArrowUpRight className="w-4 h-4" /></button>
        </div>
      </div>
    </motion.section>
  );
}
