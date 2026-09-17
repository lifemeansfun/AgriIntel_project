import React from 'react';
import { Leaf, Moon, Sun, Layers, Cpu, Radio } from '../common/Icons';
import { useTheme } from '../../context/useTheme';

export default function Navbar({ uiVersion = 'v1', setUiVersion }) {
  const { darkMode, toggleDarkMode, glassClass, textPrimary } = useTheme();

  return (
    <header className={`${glassClass} rounded-2xl px-5 py-3.5 flex justify-between items-center mb-8 relative z-20`}>
      {/* Left: Brand Identity */}
      <div className="flex items-center gap-3.5">
        <div className={`p-2.5 rounded-xl border shadow-sm ${
          darkMode
            ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-400 shadow-emerald-950/50'
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700'
        }`}>
          <Leaf className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className={`text-2xl font-editorial font-bold tracking-tight leading-none ${textPrimary}`}>
              AgriIntel
            </h1>
            <span className="text-[10px] font-mono-tech font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              v4.2
            </span>
          </div>
          <p className="text-[9px] font-mono-tech tracking-widest uppercase font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
            FRONTIER AGRICULTURAL INTELLIGENCE
          </p>
        </div>
      </div>

      {/* Center: Dual Version Switcher */}
      <div className="hidden lg:flex items-center p-1 rounded-xl border bg-black/5 dark:bg-white/5 font-mono-tech text-xs font-semibold shadow-inner">
        <button
          onClick={() => setUiVersion('v1')}
          className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${
            uiVersion === 'v1'
              ? darkMode
                ? 'bg-slate-700 text-white shadow-md'
                : 'bg-white text-emerald-950 shadow-md border border-slate-200'
              : darkMode
              ? 'text-slate-400 hover:text-white'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          V1 Cockpit
        </button>
        <button
          onClick={() => setUiVersion('v2')}
          className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${
            uiVersion === 'v2'
              ? darkMode
                ? 'bg-emerald-600 text-white shadow-md'
                : 'bg-emerald-600 text-white shadow-md border border-emerald-500/20'
              : darkMode
              ? 'text-slate-400 hover:text-white'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          V2 Monograph
        </button>
      </div>

      {/* Right: Satellite Coordinates & Celestial Theme Toggle */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-1.5 font-mono-tech text-[10.5px] text-emerald-600/80 dark:text-emerald-400/80">
          <Radio className="w-3.5 h-3.5 animate-pulse" />
          <span>23.7&deg;N, 76.0&deg;E</span>
        </div>

        <button
          type="button"
          onClick={toggleDarkMode}
          className={`flex items-center gap-2 p-1.5 px-3 rounded-full border transition-all cursor-pointer ${
            darkMode
              ? 'bg-slate-900/80 border-white/15 text-amber-300 hover:bg-slate-800'
              : 'bg-white/80 border-slate-200 text-slate-700 hover:bg-slate-100 shadow-sm'
          }`}
          aria-label="Toggle Celestial Day/Night Theme"
          title={darkMode ? 'Switch to Sunlight Day Mode' : 'Switch to Midnight Starry Mode'}
        >
          {darkMode ? (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span className="text-[11px] font-mono-tech font-semibold">NIGHT</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-slate-600" />
              <span className="text-[11px] font-mono-tech font-semibold">DAY</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
