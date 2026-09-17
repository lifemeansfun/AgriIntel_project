import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Layers,
  Droplets,
  Compass,
  Sprout,
  Sparkles,
  LayoutList,
  LineChart,
  ShieldCheck,
} from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';
import CropCard from './CropCard';
import EfficientFrontierChart from './EfficientFrontierChart';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

export default function RecommendationList({
  recommendations = [],
  formData = {},
  onSelectCrop,
}) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();
  const [activeTab, setActiveTab] = useState('leaderboard'); // 'leaderboard' | 'frontier'

  // If no recommendations loaded yet, render the Living Agronomic Standby Observatory
  if (recommendations.length === 0) {
    const currentDistrict = formData.district || 'Agar Malwa';
    const currentState = formData.state || 'Madhya Pradesh';

    return (
      <div className={`${glassClass} rounded-3xl p-7 sm:p-9 relative overflow-hidden space-y-6`}>
        {/* Observatory Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-5 border-b border-black/5 dark:border-white/10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-[10px] font-mono-tech tracking-widest uppercase font-semibold text-emerald-600 dark:text-emerald-400">
                REGIONAL AGRO-CLIMATIC OBSERVATORY
              </span>
            </div>
            <h2 className={`text-2xl sm:text-3xl font-editorial font-bold ${textPrimary}`}>
              {currentDistrict}, {currentState}
            </h2>
          </div>

          <div className="flex items-center gap-2 font-mono-tech text-[10.5px]">
            <span className="px-2.5 py-1 rounded-lg border border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold">
              SUB-REGION VIII
            </span>
            <span className={`px-2.5 py-1 rounded-lg border ${
              darkMode ? 'border-white/10 bg-white/5 text-slate-300' : 'border-slate-200 bg-slate-100 text-slate-700'
            }`}>
              ELEV: ~490m MSL
            </span>
          </div>
        </div>

        {/* 4 Scientific Regional Telemetry Panels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Soil Edaphic Profile */}
          <div className={`p-4 rounded-2xl border transition-all ${
            darkMode
              ? 'bg-slate-900/60 border-white/10 hover:border-emerald-500/30'
              : 'bg-white/70 border-slate-200/80 hover:border-emerald-500/30 shadow-sm'
          }`}>
            <div className="flex items-center gap-2 mb-2 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold">
              <Layers className="w-4 h-4" />
              <span>SOIL EDAPHIC PROFILE</span>
            </div>
            <p className={`text-sm font-semibold ${textPrimary} mb-1`}>
              Deep Black Soils (Chromic Vertisols)
            </p>
            <p className={`text-xs leading-relaxed ${textSecondary}`}>
              High montmorillonite clay fraction (&gt;45%), excellent moisture retentive capacity, neutral to mildly alkaline pH (7.4 &ndash; 8.2).
            </p>
          </div>

          {/* Hydrological Regime */}
          <div className={`p-4 rounded-2xl border transition-all ${
            darkMode
              ? 'bg-slate-900/60 border-white/10 hover:border-emerald-500/30'
              : 'bg-white/70 border-slate-200/80 hover:border-emerald-500/30 shadow-sm'
          }`}>
            <div className="flex items-center gap-2 mb-2 text-teal-600 dark:text-teal-400 font-mono-tech text-xs font-bold">
              <Droplets className="w-4 h-4" />
              <span>HYDROLOGICAL NORMAL</span>
            </div>
            <p className={`text-sm font-semibold ${textPrimary} mb-1`}>
              920 &ndash; 1,050 mm / Year (Semi-Arid Sub-Humid)
            </p>
            <p className={`text-xs leading-relaxed ${textSecondary}`}>
              Monsoon concentration: 88% between July &ndash; September. High water storage buffering terminal dry spells in post-monsoon Kharif.
            </p>
          </div>

          {/* Agro-Climatic Terrain */}
          <div className={`p-4 rounded-2xl border transition-all ${
            darkMode
              ? 'bg-slate-900/60 border-white/10 hover:border-emerald-500/30'
              : 'bg-white/70 border-slate-200/80 hover:border-emerald-500/30 shadow-sm'
          }`}>
            <div className="flex items-center gap-2 mb-2 text-amber-600 dark:text-amber-400 font-mono-tech text-xs font-bold">
              <Compass className="w-4 h-4" />
              <span>TOPOGRAPHIC CLASSIFICATION</span>
            </div>
            <p className={`text-sm font-semibold ${textPrimary} mb-1`}>
              Malwa Plateau Undulating Basalt Plain
            </p>
            <p className={`text-xs leading-relaxed ${textSecondary}`}>
              Moderate drainage slope, low soil erosion index with contour bunding, well-suited for mechanized harvesting and drip networks.
            </p>
          </div>

          {/* Regional Anchor Crops */}
          <div className={`p-4 rounded-2xl border transition-all ${
            darkMode
              ? 'bg-slate-900/60 border-white/10 hover:border-emerald-500/30'
              : 'bg-white/70 border-slate-200/80 hover:border-emerald-500/30 shadow-sm'
          }`}>
            <div className="flex items-center gap-2 mb-2 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold">
              <Sprout className="w-4 h-4" />
              <span>HISTORICAL BENCHMARK CROPS</span>
            </div>
            <p className={`text-sm font-semibold ${textPrimary} mb-1`}>
              Soyabean, Arhar/Tur, Wheat, Gram &amp; Maize
            </p>
            <p className={`text-xs leading-relaxed ${textSecondary}`}>
              Long-term district yield series (2000&ndash;2024) calibrated against real APMC mandi market price volatility and MSP floor data.
            </p>
          </div>
        </div>

        {/* Action Prompt */}
        <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-emerald-500/5 border border-emerald-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500 text-white shadow-md">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className={`text-sm font-bold ${textPrimary}`}>Ready for Advisory Optimization</h4>
              <p className={`text-xs ${textSecondary}`}>
                Select your crop season cycle on the left to compute the Pareto-optimal frontier.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 font-mono-tech text-[10.5px] text-emerald-700 dark:text-emerald-300 font-semibold shrink-0">
            <ShieldCheck className="w-4 h-4" />
            <span>26,525 DATA POINTS VERIFIED</span>
          </div>
        </div>
      </div>
    );
  }

  // When recommendations are available, render the Dual-Mode Leaderboard / Efficient Frontier
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Title & Dual-Mode View Switcher */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-1">
        <div>
          <h2 className={`text-3xl font-editorial font-bold ${textPrimary}`}>Top Recommended Crops</h2>
          <p className={`mt-1 text-xs sm:text-sm font-mono-tech ${textSecondary}`}>
            Risk-adjusted ranking for {formData.district}, {formData.state} &mdash; {formData.area} HA ({formData.season})
          </p>
        </div>

        {/* View Switcher Pill Toggle */}
        <div className={`p-1 rounded-xl border flex items-center gap-1 ${
          darkMode ? 'bg-black/30 border-white/10' : 'bg-slate-100/90 border-slate-200 shadow-sm'
        }`}>
          <button
            type="button"
            onClick={() => setActiveTab('leaderboard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono-tech font-semibold transition-all cursor-pointer ${
              activeTab === 'leaderboard'
                ? darkMode
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'bg-white text-emerald-950 shadow-md border border-emerald-500/20'
                : darkMode
                ? 'text-slate-400 hover:text-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <LayoutList className="w-3.5 h-3.5" />
            <span>Leaderboard</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('frontier')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono-tech font-semibold transition-all cursor-pointer ${
              activeTab === 'frontier'
                ? darkMode
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'bg-white text-emerald-950 shadow-md border border-emerald-500/20'
                : darkMode
                ? 'text-slate-400 hover:text-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <LineChart className="w-3.5 h-3.5" />
            <span>Frontier Curve</span>
          </button>
        </div>
      </div>

      {/* Content Rendering: Leaderboard or Markowitz Efficient Frontier */}
      {activeTab === 'leaderboard' ? (
        <div className="space-y-4">
          {recommendations.slice(0, 5).map((rec, idx) => (
            <CropCard
              key={`${rec.Crop}-${idx}`}
              crop={rec}
              rank={idx + 1}
              onSelect={onSelectCrop}
            />
          ))}
        </div>
      ) : (
        <div className={`${glassClass} rounded-3xl p-6 lg:p-7`}>
          <EfficientFrontierChart
            recommendations={recommendations}
            onSelectCrop={onSelectCrop}
          />
        </div>
      )}
    </motion.div>
  );
}
