import React from 'react';
import { Layers, Droplets, Compass, Sprout, ShieldCheck } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

export default function StandbyRegionalBiome({ formData }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();

  const currentDistrict = formData.district || 'Agar Malwa';
  const currentState = formData.state || 'Madhya Pradesh';

  return (
    <div className={`w-full max-w-5xl mx-auto ${glassClass} rounded-3xl p-8 sm:p-12 relative overflow-hidden space-y-12 shadow-2xl backdrop-blur-2xl`}>
      {/* Subtle Ambient Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Hero Header */}
      <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-6 border-b border-black/5 dark:border-white/10 pb-8 relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-[10px] font-bold tracking-widest uppercase">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span>Agro-Climatic Observatory Standby</span>
          </div>
          <h2 className={`text-4xl sm:text-5xl lg:text-6xl font-editorial font-bold ${textPrimary} tracking-tight leading-none`}>
            {currentDistrict}
          </h2>
          <p className={`mt-2 text-lg font-mono-tech ${textSecondary}`}>
            {currentState} &bull; Zone VIII
          </p>
        </div>

        <div className="flex flex-col items-start md:items-end gap-1.5 font-mono-tech text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>26,525 Data Points Active</span>
          </div>
          <span className={`opacity-60 px-3 py-1.5`}>
            Elevation: ~490m MSL
          </span>
        </div>
      </div>

      {/* 4 Architectural Data Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10 relative z-10">
        {/* Pillar 1 */}
        <div className="group">
          <div className="flex items-center gap-2.5 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-wider">
            <Layers className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>EDAPHIC PROFILE</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2`}>Chromic Vertisols (Deep Black Soil)</h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            High montmorillonite clay fraction (&gt;45%), excellent moisture retentive capacity, neutral to mildly alkaline pH (7.4 &ndash; 8.2). Ideal for drought buffering.
          </p>
        </div>

        {/* Pillar 2 */}
        <div className="group">
          <div className="flex items-center gap-2.5 mb-3 text-teal-600 dark:text-teal-400 font-mono-tech text-xs font-bold tracking-wider">
            <Droplets className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>HYDROLOGICAL NORMAL</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2`}>920 &ndash; 1,050 mm / Year</h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            Monsoon concentration: 88% between July &ndash; September. High water storage buffering terminal dry spells in post-monsoon Kharif.
          </p>
        </div>

        {/* Pillar 3 */}
        <div className="group">
          <div className="flex items-center gap-2.5 mb-3 text-amber-600 dark:text-amber-400 font-mono-tech text-xs font-bold tracking-wider">
            <Compass className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>TOPOGRAPHIC CLASSIFICATION</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2`}>Malwa Undulating Basalt Plain</h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            Moderate drainage slope, low soil erosion index with contour bunding, well-suited for mechanized harvesting and drip networks.
          </p>
        </div>

        {/* Pillar 4 */}
        <div className="group">
          <div className="flex items-center gap-2.5 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-wider">
            <Sprout className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>HISTORICAL BENCHMARK CROPS</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2`}>Soyabean, Tur, Wheat, Gram</h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            Long-term district yield series (2000&ndash;2024) calibrated against real APMC mandi market price volatility and MSP floor data.
          </p>
        </div>
      </div>
    </div>
  );
}
