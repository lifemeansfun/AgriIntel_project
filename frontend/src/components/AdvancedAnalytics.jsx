import React, { useMemo } from 'react';
import { Info } from './common/Icons';
import { useTheme } from '../context/useTheme';
import ErrorBoundary from './common/ErrorBoundary';
import RiskDecompositionCards from '../features/analytics/RiskDecompositionCards';
import UncertaintyChart from '../features/analytics/UncertaintyChart';

export default function AdvancedAnalytics({ crop }) {
  const { glassClass, textPrimary, textSecondary, darkMode } = useTheme();

  const yieldData = useMemo(() => {
    if (!crop) return [];
    return [
      { label: 'Pessimistic (p10)', value: Number(crop.Yield_q10?.toFixed(2) ?? 0) },
      { label: 'Median (p50)', value: Number(crop.Yield_q50?.toFixed(2) ?? 0) },
      { label: 'Optimistic (p90)', value: Number(crop.Yield_q90?.toFixed(2) ?? 0) },
    ];
  }, [crop]);

  const priceData = useMemo(() => {
    if (!crop) return [];
    return [
      { label: 'Pessimistic (p10)', value: Number(crop.Price_p10?.toFixed(0) ?? 0) },
      { label: 'Median (p50)', value: Number(crop.Price_p50?.toFixed(0) ?? 0) },
      { label: 'Optimistic (p90)', value: Number(crop.Price_p90?.toFixed(0) ?? 0) },
    ];
  }, [crop]);

  if (!crop) {
    return (
      <div className={`${glassClass} rounded-2xl p-12 text-center`}>
        <p className={`text-base ${textSecondary}`}>No crop selected for analytics.</p>
      </div>
    );
  }

  const emerald = darkMode ? '#34d399' : '#059669';
  const amber = '#D97706';

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-24">
      {/* Header */}
      <div className={`${glassClass} rounded-3xl p-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6`}>
        <div>
          <h1 className={`text-4xl font-editorial font-bold mb-2 ${textPrimary}`}>{crop.Crop}</h1>
          <p className={`flex items-center gap-2 text-sm ${textSecondary}`}>
            <Info className="w-4 h-4" />
            <span>Advanced Risk &amp; Return Decomposition</span>
          </p>
        </div>
        <div className="text-left md:text-right">
          <p className={`text-xs font-semibold uppercase tracking-widest mb-1 ${textSecondary}`}>
            Recommendation Score
          </p>
          <p className="text-4xl font-bold font-mono-tech text-emerald-500">
            {(crop.Score ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {/* Metrics Breakdown Cards */}
      <ErrorBoundary title="Risk Decomposition Metrics">
        <RiskDecompositionCards crop={crop} />
      </ErrorBoundary>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ErrorBoundary title="Yield Uncertainty Chart">
          <UncertaintyChart
            title="Yield Uncertainty Envelope (Tonnes / ha)"
            data={yieldData}
            color={emerald}
            gradientId="gYield"
          />
        </ErrorBoundary>

        <ErrorBoundary title="Price Uncertainty Chart">
          <UncertaintyChart
            title="Price Uncertainty Envelope (₹ / Quintal)"
            data={priceData}
            color={amber}
            gradientId="gPrice"
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
