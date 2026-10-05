import React from 'react';
import { Layers, Droplets, Compass, Sprout, ShieldCheck, Activity } from '../../components/common/Icons';
import { useTheme } from '../../context/useTheme';

const STATE_BIOMES = {
  'Madhya Pradesh': {
    zone: 'Zone VIII • Central Plateau & Hills',
    elevation: '~490m MSL',
    edaphicTitle: 'Chromic Vertisols (Deep Black Cotton Soil)',
    edaphicDesc: 'High montmorillonite clay fraction (>45%), exceptional moisture-holding capacity, neutral to mildly alkaline pH (7.4–8.2). High drought buffering.',
    hydroTitle: '920 – 1,050 mm / Year',
    hydroDesc: 'Monsoon concentration: 88% between July – September. High sub-soil moisture storage buffering post-monsoon terminal dry spells in Kharif.',
    topoTitle: 'Malwa Undulating Basalt Plain',
    topoDesc: 'Moderate drainage gradient, low-to-moderate runoff slope, ideally suited for contour bunding and mechanized ridge planting.',
    benchmarkTitle: 'Soyabean, Tur, Wheat, Gram',
    benchmarkDesc: 'Calibrated on 24-year district time-series (2000–2024) across verified APMC mandis and central CACP MSP benchmarks.'
  },
  'Maharashtra': {
    zone: 'Zone IX • Western Plateau & Hills',
    elevation: '~560m MSL',
    edaphicTitle: 'Pellic Vertisols & Deep Regur (Black Soil)',
    edaphicDesc: 'Formed from Deccan trap basalt lava flows; rich in calcium, magnesium, and potassium; high CEC (>50 cmol/kg) with high shrink-swell dynamics.',
    hydroTitle: '720 – 1,150 mm / Year',
    hydroDesc: 'Bimodal south-west monsoon pattern with rain-shadow variability; high responsiveness to localized micro-irrigation and farm ponds.',
    topoTitle: 'Deccan Basalt Lava Plateau',
    topoDesc: 'Stepped trappean terracing and broad valley plains, highly responsive to moisture conservation and localized fertigation.',
    benchmarkTitle: 'Cotton, Soyabean, Sugarcane, Jowar, Onion',
    benchmarkDesc: 'Multi-decade agricultural census telemetry aligned with APMC Lasalgaon and Pune district price distributions.'
  },
  'Punjab': {
    zone: 'Zone VI • Trans-Gangetic Plain',
    elevation: '~240m MSL',
    edaphicTitle: 'Indo-Gangetic Alluvium (Inceptisols & Entisols)',
    edaphicDesc: 'Deep, fertile loam to sandy-loam with balanced mineral profiles, low organic carbon requiring structured residue and nitrogen management.',
    hydroTitle: '650 – 820 mm / Year',
    hydroDesc: '98% assured canal and tubewell irrigation network; high water productivity under synchronized paddy-wheat crop rotations.',
    topoTitle: 'Perennial Alluvial Riverine Plain',
    topoDesc: 'Extremely flat topography (<0.1% gradient) enabling precision laser land leveling, direct-seeded rice, and automated combine harvesting.',
    benchmarkTitle: 'Wheat, Rice, Cotton, Maize, Mustard',
    benchmarkDesc: 'Highest crop yield density in South Asia, benchmarked against rigorous procurement mandis and FCI procurement quotas.'
  },
  'Tamil Nadu': {
    zone: 'Zone X & XI • Southern Plateau & Coastal Plains',
    elevation: '~180m MSL',
    edaphicTitle: 'Alfisols (Red Loam) & Coastal Vertisols',
    edaphicDesc: 'Well-drained red loam with porous crumb structure in inland tracts; deltaic heavy clays in the Cauvery basin with high fertility.',
    hydroTitle: '880 – 1,100 mm / Year',
    hydroDesc: 'Unique North-East retreating monsoon peak (October–December) providing crucial filling water for Samba and Thaladi seasons.',
    topoTitle: 'Coromandel Coastal & Inland Peneplain',
    topoDesc: 'Gently undulating hard rock terrain with intricate tank-cascade irrigation networks and deltaic canal sluices.',
    benchmarkTitle: 'Paddy, Groundnut, Sugarcane, Millets, Cotton',
    benchmarkDesc: 'Calibrated against Tamil Nadu agricultural census and regional Uzhavar Sandhai price series.'
  },
  'Uttar Pradesh': {
    zone: 'Zone V • Upper & Middle Gangetic Plain',
    elevation: '~130m MSL',
    edaphicTitle: 'Gangetic Deep Silt-Loam Alluvium',
    edaphicDesc: 'Perennially replenished deep alluvial silt, high natural fertility, neutral pH, excellent capillary action for rabi wheat and sugarcane.',
    hydroTitle: '850 – 1,020 mm / Year',
    hydroDesc: 'South-west monsoon dominance (June–September) complemented by Western Disturbances winter precipitation for rabi crops.',
    topoTitle: 'Gangetic Fertile Lowland Basin',
    topoDesc: 'Expansive fertile floodplains with high groundwater tables, ideal for multi-tier intercropping and deep root systems.',
    benchmarkTitle: 'Sugarcane, Wheat, Rice, Mustard, Potato',
    benchmarkDesc: 'Synchronized with Western & Eastern UP mandi corridors and statutory SAP sugarcane pricing.'
  }
};

export default function StandbyRegionalBiome({ formData }) {
  const { glassClass, textPrimary, textSecondary } = useTheme();

  const currentDistrict = formData.district || 'Agar Malwa';
  const currentState = formData.state || 'Madhya Pradesh';

  const biome = STATE_BIOMES[currentState] || STATE_BIOMES['Madhya Pradesh'];

  return (
    <div className={`w-full max-w-5xl mx-auto ${glassClass} rounded-[2.5rem] p-8 sm:p-12 relative overflow-hidden space-y-12 shadow-2xl backdrop-blur-2xl border border-white/20 dark:border-white/10`}>
      {/* Subtle Ambient Glow */}
      <div className="absolute top-0 right-0 w-[450px] h-[450px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Hero Header */}
      <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-6 border-b border-black/5 dark:border-white/10 pb-8 relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-widest uppercase">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            <span>Agro-Climatic Observatory Standby</span>
          </div>
          <h2 className={`text-4xl sm:text-5xl lg:text-6xl font-editorial font-bold ${textPrimary} tracking-tight leading-none`}>
            {currentDistrict}
          </h2>
          <p className={`mt-2 text-base sm:text-lg font-mono-tech ${textSecondary}`}>
            {currentState} &bull; {biome.zone}
          </p>
        </div>

        <div className="flex flex-col items-start md:items-end gap-2 font-mono-tech text-xs">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold shadow-sm">
            <ShieldCheck className="w-4 h-4" />
            <span>26,525 Calibrated Micro-Observations</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 text-slate-600 dark:text-slate-400">
            <Activity className="w-3.5 h-3.5 text-teal-500" />
            <span>Elevation: {biome.elevation}</span>
          </div>
        </div>
      </div>

      {/* 4 Architectural Data Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10 relative z-10">
        {/* Pillar 1: Edaphic Profile */}
        <div className="group p-5 rounded-2xl border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-all">
          <div className="flex items-center gap-2.5 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-wider uppercase">
            <Layers className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>EDAPHIC PROFILE</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2 leading-snug`}>
            {biome.edaphicTitle}
          </h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            {biome.edaphicDesc}
          </p>
        </div>

        {/* Pillar 2: Hydrological Normal */}
        <div className="group p-5 rounded-2xl border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-all">
          <div className="flex items-center gap-2.5 mb-3 text-teal-600 dark:text-teal-400 font-mono-tech text-xs font-bold tracking-wider uppercase">
            <Droplets className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>HYDROLOGICAL NORMAL</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2 leading-snug`}>
            {biome.hydroTitle}
          </h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            {biome.hydroDesc}
          </p>
        </div>

        {/* Pillar 3: Topographic Classification */}
        <div className="group p-5 rounded-2xl border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-all">
          <div className="flex items-center gap-2.5 mb-3 text-amber-600 dark:text-amber-400 font-mono-tech text-xs font-bold tracking-wider uppercase">
            <Compass className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>TOPOGRAPHIC CLASSIFICATION</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2 leading-snug`}>
            {biome.topoTitle}
          </h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            {biome.topoDesc}
          </p>
        </div>

        {/* Pillar 4: Historical Benchmark Crops */}
        <div className="group p-5 rounded-2xl border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-all">
          <div className="flex items-center gap-2.5 mb-3 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-wider uppercase">
            <Sprout className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span>HISTORICAL BENCHMARK CROPS</span>
          </div>
          <h3 className={`text-xl font-editorial font-bold ${textPrimary} mb-2 leading-snug`}>
            {biome.benchmarkTitle}
          </h3>
          <p className={`text-sm leading-relaxed ${textSecondary}`}>
            {biome.benchmarkDesc}
          </p>
        </div>
      </div>
    </div>
  );
}
