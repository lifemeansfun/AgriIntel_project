import React, { useState } from 'react';
import { useTheme } from '../../context/useTheme';
import { Sparkles, ShieldCheck } from '../../components/common/Icons';

export default function ParetoWaveChart({ recommendations = [], onSelectCrop, activeCrop }) {
  const { darkMode, textSecondary } = useTheme();
  const [hoveredCrop, setHoveredCrop] = useState(null);

  if (!recommendations || recommendations.length === 0) return null;

  // Chart dimensions & margins
  const width = 680;
  const height = 280; // slightly shorter for V2 layout
  const padLeft = 60;
  const padRight = 30;
  const padTop = 20;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Compute domains
  const risks = recommendations.map((r) => r.Downside_Risk ?? 0);
  const profits = recommendations.map((r) => r.Expected_Profit ?? 0);

  const minRisk = Math.max(0, Math.min(...risks) * 0.85);
  const maxRisk = Math.max(...risks, 1000) * 1.15;
  const minProfit = Math.min(...profits) * 0.85;
  const maxProfit = Math.max(...profits, 5000) * 1.12;

  // Coordinate mapping functions
  const getX = (val) => padLeft + ((val - minRisk) / Math.max(1, maxRisk - minRisk)) * plotW;
  const getY = (val) => height - padBottom - ((val - minProfit) / Math.max(1, maxProfit - minProfit)) * plotH;

  // Identify Pareto-optimal points
  const sortedByRisk = [...recommendations].sort((a, b) => (a.Downside_Risk ?? 0) - (b.Downside_Risk ?? 0));
  const paretoPoints = [];
  let currentMaxProfit = -Infinity;
  for (const c of sortedByRisk) {
    const p = c.Expected_Profit ?? 0;
    if (p > currentMaxProfit) {
      paretoPoints.push(c);
      currentMaxProfit = p;
    }
  }

  // Generate SVG path for the Efficient Frontier curve
  const frontierPath = paretoPoints.length > 1
    ? paretoPoints.reduce((acc, pt, idx) => {
        const x = getX(pt.Downside_Risk ?? 0);
        const y = getY(pt.Expected_Profit ?? 0);
        return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
      }, '')
    : '';

  return (
    <div className="w-full max-w-5xl mx-auto mt-8 relative select-none">
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-mono-tech text-[10px] font-bold tracking-widest uppercase mb-1">
          <Sparkles className="w-3 h-3" />
          <span>PARETO EFFICIENCY WAVE</span>
        </div>
        <p className={`text-[10px] font-mono-tech ${textSecondary}`}>Expected Profit vs Tail Risk</p>
      </div>

      <div className={`w-full overflow-hidden rounded-3xl border ${darkMode ? 'border-white/10 bg-black/20' : 'border-black/5 bg-black/5'} shadow-inner`}>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible" style={{ maxHeight: '320px' }}>
          <defs>
            <linearGradient id="paretoGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>
            <pattern id="paretoGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke={darkMode ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)'} strokeWidth="1" />
            </pattern>
          </defs>

          <rect x={padLeft} y={padTop} width={plotW} height={plotH} fill="url(#paretoGrid)" />

          {/* Grid Labels (Minimal) */}
          {[0.33, 0.66, 1.0].map((frac) => {
            const yVal = minProfit + (maxProfit - minProfit) * frac;
            const y = getY(yVal);
            return (
              <text key={`y-${frac}`} x={padLeft - 10} y={y + 3} textAnchor="end" className="font-mono-tech text-[9px] fill-slate-400 dark:fill-slate-500">
                &#8377;{Math.round(yVal / 1000)}k
              </text>
            );
          })}

          {[0.33, 0.66, 1.0].map((frac) => {
            const xVal = minRisk + (maxRisk - minRisk) * frac;
            const x = getX(xVal);
            return (
              <text key={`x-${frac}`} x={x} y={height - padBottom + 14} textAnchor="middle" className="font-mono-tech text-[9px] fill-slate-400 dark:fill-slate-500">
                &#8377;{Math.round(xVal / 1000)}k
              </text>
            );
          })}

          {/* Pareto Efficient Frontier Line */}
          {frontierPath && (
            <path d={frontierPath} fill="none" stroke="#10B981" strokeWidth="2" strokeDasharray="4 4" className="opacity-80" />
          )}

          {/* Crop Nodes */}
          {recommendations.map((crop) => {
            const cx = getX(crop.Downside_Risk ?? 0);
            const cy = getY(crop.Expected_Profit ?? 0);
            const isHovered = hoveredCrop?.Crop === crop.Crop;
            const isActive = activeCrop?.Crop === crop.Crop;
            const isPareto = paretoPoints.some((p) => p.Crop === crop.Crop);

            return (
              <g
                key={crop.Crop}
                className="cursor-pointer transition-transform duration-300"
                onMouseEnter={() => setHoveredCrop(crop)}
                onMouseLeave={() => setHoveredCrop(null)}
                onClick={() => onSelectCrop(crop)}
                style={{ transformOrigin: `${cx}px ${cy}px`, transform: isHovered || isActive ? 'scale(1.2)' : 'scale(1)' }}
              >
                {/* Active Halo */}
                {(isHovered || isActive) && (
                  <circle cx={cx} cy={cy} r={14} fill="#10B981" opacity={darkMode ? 0.2 : 0.1} />
                )}

                <circle
                  cx={cx} cy={cy} r={6}
                  fill={isActive ? '#10B981' : isPareto ? '#34d399' : darkMode ? '#334155' : '#cbd5e1'}
                  stroke={darkMode ? '#0f172a' : '#ffffff'} strokeWidth="1.5"
                />

                {(isHovered || isActive) && (
                  <text
                    x={cx} y={cy - 12} textAnchor="middle"
                    className={`font-mono-tech text-[9px] font-bold ${isActive ? 'fill-emerald-600 dark:fill-emerald-400' : 'fill-slate-700 dark:fill-slate-300'}`}
                  >
                    {crop.Crop}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay (Absolute inside container) */}
        {hoveredCrop && (
          <div
            className={`absolute top-4 right-4 p-3 rounded-xl border shadow-lg backdrop-blur-md z-30 pointer-events-none w-48 ${
              darkMode ? 'bg-slate-900/90 border-emerald-500/30 text-white' : 'bg-white/95 border-emerald-500/20 text-slate-900'
            }`}
          >
            <h4 className="font-editorial font-bold text-sm leading-tight mb-1">{hoveredCrop.Crop}</h4>
            <div className="grid grid-cols-2 gap-y-2 gap-x-1 text-[9px] font-mono-tech">
              <div>
                <span className="opacity-60 block text-[8px]">EXP. PROFIT</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">&#8377;{Math.round(hoveredCrop.Expected_Profit ?? 0).toLocaleString()}</span>
              </div>
              <div>
                <span className="opacity-60 block text-[8px]">VaR 95%</span>
                <span className="font-bold text-amber-600 dark:text-amber-400">&#8377;{Math.round(hoveredCrop.Pessimistic_Profit ?? 0).toLocaleString()}</span>
              </div>
            </div>
            {hoveredCrop.Expected_Profit > hoveredCrop.Downside_Risk && (
               <div className="mt-2 pt-1 border-t border-black/5 dark:border-white/10 text-[8px] font-mono-tech text-emerald-600 flex items-center gap-1">
                 <ShieldCheck className="w-2.5 h-2.5" /> High Ag-Sharpe
               </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
