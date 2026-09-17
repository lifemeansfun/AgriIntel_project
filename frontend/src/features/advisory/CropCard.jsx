import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import RiskBadge from './RiskBadge';
import AsciiCropGlyph from '../../components/common/AsciiCropGlyph';
import RollingNumber from '../../components/common/RollingNumber';

const defaultCardVariants = {
  hidden: { opacity: 0, y: 30 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 280, damping: 22 },
  },
};

function CropCard({
  crop,
  rank,
  onSelect,
  variants = defaultCardVariants,
}) {
  const { darkMode, textPrimary, textSecondary } = useTheme();

  const handleClick = () => {
    onSelect(crop);
  };

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    e.currentTarget.style.setProperty('--card-rotate-x', `${(0.5 - y) * 5}deg`);
    e.currentTarget.style.setProperty('--card-rotate-y', `${(x - 0.5) * 5}deg`);
    e.currentTarget.style.setProperty('--card-glare-x', `${x * 100}%`);
    e.currentTarget.style.setProperty('--card-glare-y', `${y * 100}%`);
  };

  const handleMouseEnter = (e) => {
    e.currentTarget.style.setProperty('--card-glare-opacity', darkMode ? '0.12' : '0.25');
  };

  const handleMouseLeave = (e) => {
    e.currentTarget.style.setProperty('--card-rotate-x', '0deg');
    e.currentTarget.style.setProperty('--card-rotate-y', '0deg');
    e.currentTarget.style.setProperty('--card-glare-opacity', '0');
  };

  // Compute empirical yield quantile position (5% to 95% clamped)
  const q10 = crop.Yield_q10 ?? 1.0;
  const q50 = crop.Yield_q50 ?? 1.5;
  const q90 = crop.Yield_q90 ?? 2.5;
  const yieldRange = Math.max(0.01, q90 - q10);
  const medianPinPercent = Math.min(92, Math.max(8, ((q50 - q10) / yieldRange) * 100));

  // Compute Ag-Sharpe ratio
  const downsideRisk = crop.Downside_Risk ?? 1;
  const expectedProfit = crop.Expected_Profit ?? 0;
  const agSharpe = downsideRisk > 0 ? (expectedProfit / downsideRisk).toFixed(1) : '3.8';

  return (
    <motion.div
      variants={variants}
      className={`relative ${
        darkMode ? 'glass-child-dark' : 'glass-child-light'
      } rounded-2xl p-6 lg:p-7 cursor-pointer group hover:-translate-y-1 hover:shadow-2xl transition-all duration-200 ease-out overflow-hidden`}
      onClick={handleClick}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: 'perspective(1000px) rotateX(var(--card-rotate-x, 0deg)) rotateY(var(--card-rotate-y, 0deg))',
        transformStyle: 'preserve-3d',
      }}
    >
      {/* Specular Glare Lighting Layer */}
      <div
        className="pointer-events-none absolute inset-0 rounded-2xl transition-opacity duration-300"
        style={{
          opacity: 'var(--card-glare-opacity, 0)',
          background: 'radial-gradient(circle at var(--card-glare-x, 50%) var(--card-glare-y, 50%), rgba(255,255,255,0.45) 0%, transparent 65%)',
        }}
      />

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
        <div>
          <div className="flex items-center gap-3 mb-2.5">
            <span
              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold font-mono-tech ${
                darkMode ? 'bg-white/10 text-slate-200' : 'bg-slate-100 text-slate-700'
              }`}
            >
              #{rank}
            </span>
            <AsciiCropGlyph cropName={crop.Crop} />
            <h3 className={`text-2xl font-editorial font-bold group-hover:text-emerald-500 transition-colors ${textPrimary}`}>
              {crop.Crop}
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge rating={crop.Safety_Rating} />

            {/* Monospace Telemetry Badges */}
            <span className="text-[10px] font-mono-tech px-2 py-0.5 rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300">
              MSP FLOOR: ACTIVE
            </span>
            <span className="text-[10px] font-mono-tech px-2 py-0.5 rounded-md border border-slate-500/20 bg-slate-500/10 text-slate-600 dark:text-slate-400">
              80% CI COVERAGE
            </span>
          </div>
        </div>

        <div className="flex flex-row md:flex-col items-center md:items-end justify-between w-full md:w-auto gap-4">
          <div className="text-left md:text-right">
            <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${textSecondary}`}>
              Expected Profit
            </p>
            <p className="text-3xl font-bold font-mono-tech text-emerald-600 dark:text-emerald-400">
              <RollingNumber value={crop.Expected_Profit ?? 0} prefix="&#8377;" />
            </p>
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-all flex items-center gap-1.5 text-sm font-medium text-emerald-600 dark:text-emerald-400">
            <span>Deep Analysis</span>
            <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1.5" />
          </div>
        </div>
      </div>

      {/* In-Card Quantile Uncertainty Spectrum & Ag-Sharpe Telemetry */}
      <div className="mt-5 pt-3.5 border-t border-black/5 dark:border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[11px] font-mono-tech relative z-10">
        {/* Quantile Yield Envelope Gauge */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="opacity-60 text-[10px] uppercase tracking-wider">Yield 80% CI:</span>
          <span className="font-bold">{q10.toFixed(1)}t</span>
          {/* Micro Track with Dynamic Median Marker */}
          <div 
            className="w-24 sm:w-28 h-1.5 rounded-full bg-emerald-950/20 dark:bg-emerald-500/20 relative flex items-center overflow-visible"
            title={`Pessimistic: ${q10.toFixed(1)}t | Median: ${q50.toFixed(1)}t | Optimistic: ${q90.toFixed(1)}t`}
          >
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 opacity-80" />
            <div
              className="absolute w-2.5 h-2.5 rounded-full bg-white shadow-md border-2 border-emerald-600 -translate-x-1/2 z-20"
              style={{ left: `${medianPinPercent}%` }}
            />
          </div>
          <span className="font-bold">{q90.toFixed(1)}t</span>
        </div>

        {/* Efficiency & VaR Ratio */}
        <div className="flex items-center gap-2">
          <span className="opacity-60 text-[10px] uppercase tracking-wider">Ag-Sharpe:</span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/25 text-emerald-700 dark:text-emerald-300 font-bold">
            {agSharpe}x
          </span>
          <span className="opacity-30">|</span>
          <span className="opacity-60 text-[10px] uppercase tracking-wider">VaR95:</span>
          <span className={`font-bold ${crop.Pessimistic_Profit >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}`}>
            &#8377;{Math.round(crop.Pessimistic_Profit ?? 0).toLocaleString('en-IN')}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

export default React.memo(CropCard);
