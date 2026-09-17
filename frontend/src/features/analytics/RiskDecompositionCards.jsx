import React from 'react';
import { TrendingUp, TrendingDown } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

export default function RiskDecompositionCards({ crop }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  if (!crop) return null;

  const expectedProfit = (crop.Expected_Profit ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  const downsideRisk = (crop.Downside_Risk ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  const costPerHa = (crop.Cost_per_ha ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Expected Profit */}
      <div className={`${glassClass} rounded-3xl p-8`}>
        <h3 className={`text-base font-semibold mb-6 flex items-center gap-2 ${textPrimary}`}>
          <TrendingUp className="w-5 h-5 text-emerald-500" />
          <span>Total Expected Profit</span>
        </h3>
        <p className="text-5xl font-bold text-emerald-600 mb-4">
          {'\u20B9'}{expectedProfit}
        </p>
        <p className={`text-sm leading-relaxed border-t pt-4 ${textSecondary} ${darkMode ? 'border-white/10' : 'border-slate-200'}`}>
          Computed from the median yield (q50) and median market price (p50), after subtracting
          standard cultivation costs of {'\u20B9'}{costPerHa} per hectare.
        </p>
      </div>

      {/* Downside Risk */}
      <div className={`${glassClass} rounded-3xl p-8`}>
        <h3 className={`text-base font-semibold mb-6 flex items-center gap-2 ${textPrimary}`}>
          <TrendingDown className="w-5 h-5 text-rose-500" />
          <span>Downside Risk Penalty</span>
        </h3>
        <p className="text-5xl font-bold text-rose-500 mb-4">
          {'\u20B9'}{downsideRisk}
        </p>
        <p className={`text-sm leading-relaxed border-t pt-4 ${textSecondary} ${darkMode ? 'border-white/10' : 'border-slate-200'}`}>
          The gap between the expected profit and the worst-case pessimistic scenario (p10 yield
          at p10 price). This is your maximum likely financial exposure to crop failure or a market glut.
        </p>
      </div>
    </div>
  );
}
