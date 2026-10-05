import React, { useState } from 'react';
import { useTheme } from '../../context/useTheme';
import { Sparkles, TrendingUp, AlertTriangle } from '../../components/common/Icons';

export default function ParetoWaveChart({ recommendations = [], onSelectCrop, activeCrop }) {
  const { glassClass, darkMode, textPrimary, textSecondary } = useTheme();
  const [hoveredCrop, setHoveredCrop] = useState(null);

  if (!recommendations || recommendations.length === 0) return null;

  // Chart dimensions & margins
  const width = 760;
  const height = 320;
  const padLeft = 80;
  const padRight = 40;
  const padTop = 35;
  const padBottom = 55;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  // Compute domains
  const risks = recommendations.map((r) => Number(r.Downside_Risk ?? 0));
  const profits = recommendations.map((r) => Number(r.Expected_Profit ?? 0));

  const minRisk = Math.max(0, Math.min(...risks) * 0.85);
  const maxRisk = Math.max(...risks, 1000) * 1.15;
  const minProfit = Math.min(...profits) * 0.85;
  const maxProfit = Math.max(...profits, 5000) * 1.15;

  // Coordinate mapping functions
  const getX = (val) => padLeft + ((val - minRisk) / Math.max(1, maxRisk - minRisk)) * plotW;
  const getY = (val) => height - padBottom - ((val - minProfit) / Math.max(1, maxProfit - minProfit)) * plotH;

  // Identify Pareto-optimal points
  const sortedByRisk = [...recommendations].sort((a, b) => (Number(a.Downside_Risk ?? 0) - Number(b.Downside_Risk ?? 0)));
  const paretoPoints = [];
  let currentMaxProfit = -Infinity;
  for (const c of sortedByRisk) {
    const p = Number(c.Expected_Profit ?? 0);
    if (p > currentMaxProfit) {
      paretoPoints.push(c);
      currentMaxProfit = p;
    }
  }

  // Generate SVG path for the Efficient Frontier curve
  const frontierPath = paretoPoints.length > 1
    ? paretoPoints.reduce((acc, pt, idx) => {
        const x = getX(Number(pt.Downside_Risk ?? 0));
        const y = getY(Number(pt.Expected_Profit ?? 0));
        return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
      }, '')
    : '';

  // Area fill beneath the frontier
  const firstPt = paretoPoints[0];
  const lastPt = paretoPoints[paretoPoints.length - 1];
  const areaPath = paretoPoints.length > 1 && firstPt && lastPt
    ? `${frontierPath} L ${getX(Number(lastPt.Downside_Risk ?? 0))} ${height - padBottom} L ${getX(Number(firstPt.Downside_Risk ?? 0))} ${height - padBottom} Z`
    : '';

  return (
    <div className={`w-full max-w-5xl mx-auto mt-10 ${glassClass} rounded-3xl p-6 sm:p-8 border border-white/20 dark:border-white/10 shadow-2xl backdrop-blur-2xl relative select-none`}>
      
      {/* Dedicated Header Bar - Completely decoupled from SVG canvas coordinates */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-black/5 dark:border-white/10">
        <div>
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-mono-tech text-xs font-bold tracking-widest uppercase mb-1">
            <span className="p-1 rounded-md bg-emerald-500/10 border border-emerald-500/20">
              <Sparkles className="w-3.5 h-3.5" />
            </span>
            <span>PARETO EFFICIENCY WAVE</span>
          </div>
          <p className={`text-xs font-mono-tech ${textSecondary}`}>
            Expected Profit vs Tail Risk (Markowitz-Hull Frontier Calibration)
          </p>
        </div>

        {/* Legend Indicators */}
        <div className="flex items-center gap-4 text-xs font-mono-tech">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 border border-white dark:border-slate-900 shadow-sm" />
            <span className={textSecondary}>Pareto Frontier</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-600" />
            <span className={textSecondary}>Sub-optimal</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas Container with Crisp Dark/Light Contrast Shield */}
      <div className={`w-full overflow-hidden rounded-2xl border ${darkMode ? 'border-white/10 bg-black/40' : 'border-slate-200/80 bg-white/70'} shadow-inner relative`}>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible" style={{ maxHeight: '340px' }}>
          <defs>
            <linearGradient id="paretoAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>
            
            <pattern id="paretoGridFine" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke={darkMode ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'} strokeWidth="1" />
            </pattern>
          </defs>

          {/* Grid Area */}
          <rect x={padLeft} y={padTop} width={plotW} height={plotH} fill="url(#paretoGridFine)" rx="8" />

          {/* Area Fill Under Frontier */}
          {areaPath && (
            <path d={areaPath} fill="url(#paretoAreaGrad)" />
          )}

          {/* Y-Axis Horizontal Gridlines & Labels */}
          {[0.25, 0.5, 0.75, 1.0].map((frac) => {
            const yVal = minProfit + (maxProfit - minProfit) * frac;
            const y = getY(yVal);
            return (
              <g key={`y-${frac}`}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={darkMode ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)'}
                  strokeDasharray="2 4"
                />
                <text
                  x={padLeft - 12}
                  y={y + 4}
                  textAnchor="end"
                  className={`font-mono-tech text-[10px] font-semibold ${darkMode ? 'fill-slate-400' : 'fill-slate-600'}`}
                >
                  &#8377;{Math.round(yVal / 1000)}k
                </text>
              </g>
            );
          })}

          {/* X-Axis Vertical Gridlines & Labels */}
          {[0.25, 0.5, 0.75, 1.0].map((frac) => {
            const xVal = minRisk + (maxRisk - minRisk) * frac;
            const x = getX(xVal);
            return (
              <g key={`x-${frac}`}>
                <line
                  x1={x}
                  y1={padTop}
                  x2={x}
                  y2={height - padBottom}
                  stroke={darkMode ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)'}
                  strokeDasharray="2 4"
                />
                <text
                  x={x}
                  y={height - padBottom + 18}
                  textAnchor="middle"
                  className={`font-mono-tech text-[10px] font-semibold ${darkMode ? 'fill-slate-400' : 'fill-slate-600'}`}
                >
                  &#8377;{Math.round(xVal / 1000)}k
                </text>
              </g>
            );
          })}

          {/* Axis Labels */}
          <text
            x={padLeft + 10}
            y={padTop + 14}
            className={`font-mono-tech text-[10px] font-bold uppercase tracking-wider ${darkMode ? 'fill-emerald-400' : 'fill-emerald-700'}`}
          >
            Expected Return &#8593;
          </text>
          
          <text
            x={width - padRight}
            y={height - padBottom + 35}
            textAnchor="end"
            className={`font-mono-tech text-[10px] font-bold uppercase tracking-wider ${darkMode ? 'fill-slate-400' : 'fill-slate-600'}`}
          >
            Downside Tail Risk (VaR95) &#8594;
          </text>

          {/* Pareto Efficient Frontier Line */}
          {frontierPath && (
            <path
              d={frontierPath}
              fill="none"
              stroke="#10B981"
              strokeWidth="2.5"
              strokeDasharray="6 4"
              className="drop-shadow-[0_2px_8px_rgba(16,185,129,0.4)]"
            />
          )}

          {/* Crop Nodes */}
          {recommendations.map((crop) => {
            const cx = getX(Number(crop.Downside_Risk ?? 0));
            const cy = getY(Number(crop.Expected_Profit ?? 0));
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
                style={{ transformOrigin: `${cx}px ${cy}px`, transform: isHovered || isActive ? 'scale(1.25)' : 'scale(1)' }}
              >
                {/* Active Halo */}
                {(isHovered || isActive) && (
                  <circle cx={cx} cy={cy} r={18} fill="#10B981" opacity={darkMode ? 0.3 : 0.2} className="animate-pulse" />
                )}

                {/* Outer Ring */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isActive ? 8 : 6}
                  fill={isActive ? '#10B981' : isPareto ? '#34d399' : darkMode ? '#475569' : '#cbd5e1'}
                  stroke={darkMode ? '#0f172a' : '#ffffff'}
                  strokeWidth="2"
                  className="shadow-md"
                />

                {/* Inner Core */}
                {isActive && (
                  <circle cx={cx} cy={cy} r={3.5} fill="#ffffff" />
                )}

                {/* Crop Name Badge */}
                {(isHovered || isActive || isPareto) && (
                  <text
                    x={cx}
                    y={cy - 14}
                    textAnchor="middle"
                    className={`font-mono-tech text-[10px] font-bold ${
                      isActive 
                        ? 'fill-emerald-600 dark:fill-emerald-400 font-extrabold' 
                        : isHovered 
                        ? darkMode ? 'fill-white' : 'fill-slate-900' 
                        : darkMode ? 'fill-slate-300' : 'fill-slate-700'
                    }`}
                  >
                    {crop.Crop}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay (Floating Glass Pill) */}
        {hoveredCrop && (
          <div
            className={`absolute top-4 right-4 p-4 rounded-2xl border shadow-2xl backdrop-blur-xl z-30 pointer-events-none w-56 ${
              darkMode ? 'bg-slate-900/95 border-emerald-500/40 text-white' : 'bg-white/95 border-emerald-500/30 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-editorial font-bold text-base leading-tight">{hoveredCrop.Crop}</h4>
              <span className="text-[10px] font-mono-tech px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold">
                {paretoPoints.some(p => p.Crop === hoveredCrop.Crop) ? 'FRONTIER' : 'CANDIDATE'}
              </span>
            </div>
            
            <div className="space-y-1.5 font-mono-tech text-xs">
              <div className="flex items-center justify-between">
                <span className={`text-[10px] ${textSecondary}`}>EXP. PROFIT:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  &#8377;{Math.round(hoveredCrop.Expected_Profit ?? 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className={`text-[10px] ${textSecondary}`}>TAIL RISK (VaR):</span>
                <span className={`font-bold ${(hoveredCrop.Pessimistic_Profit ?? 0) >= 0 ? textPrimary : 'text-rose-500'}`}>
                  &#8377;{Math.round(hoveredCrop.Pessimistic_Profit ?? 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-black/5 dark:border-white/10">
                <span className={`text-[10px] ${textSecondary}`}>AG-SHARPE:</span>
                <span className="font-bold text-teal-600 dark:text-teal-400">
                  {((hoveredCrop.Expected_Profit ?? 0) / Math.max(1, hoveredCrop.Downside_Risk ?? 1)).toFixed(2)}x
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
