import React, { useState } from 'react';
import { useTheme } from '../../context/useTheme';
import { ArrowUpRight, Sparkles, ShieldCheck } from '../../components/common/Icons';
import AsciiCropGlyph from '../../components/common/AsciiCropGlyph';

export default function EfficientFrontierChart({ recommendations = [], onSelectCrop }) {
  const { darkMode, textPrimary, textSecondary } = useTheme();
  const [hoveredCrop, setHoveredCrop] = useState(null);

  if (!recommendations || recommendations.length === 0) return null;

  // Chart dimensions & margins
  const width = 680;
  const height = 360;
  const padLeft = 70;
  const padRight = 50;
  const padTop = 40;
  const padBottom = 55;
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

  // Identify Pareto-optimal points (Non-dominated: higher profit for given or lower risk)
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
    <div className="space-y-4">
      {/* Header & Meta Explanation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-500" />
            <h3 className={`text-base font-bold ${textPrimary}`}>
              Markowitz Risk-Return Efficient Frontier
            </h3>
            <span className="text-[10px] font-mono-tech px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
              PARETO-OPTIMAL
            </span>
          </div>
          <p className={`text-xs ${textSecondary} mt-0.5 font-mono-tech`}>
            Upper-left boundary represents maximum expected return per unit of downside tail risk.
          </p>
        </div>

        <div className="flex items-center gap-3 font-mono-tech text-[10px]">
          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold">
            <span className="w-3 h-0.5 bg-emerald-500 inline-block" /> Frontier Curve
          </span>
          <span className="flex items-center gap-1 text-slate-500">
            <span className="w-2 h-2 rounded-full border border-slate-400 inline-block" /> Crop Portfolio
          </span>
        </div>
      </div>

      {/* SVG Interactive Coordinate Plane */}
      <div className="relative w-full overflow-hidden rounded-2xl border border-black/5 dark:border-white/10 bg-black/5 dark:bg-black/30 p-2 select-none">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          style={{ maxHeight: '420px' }}
        >
          <defs>
            {/* Gradient for Frontier Area */}
            <linearGradient id="frontierAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity={darkMode ? '0.25' : '0.15'} />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>

            {/* Grid Pattern */}
            <pattern id="frontierGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke={darkMode ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'}
                strokeWidth="1"
              />
            </pattern>
          </defs>

          {/* Grid Background */}
          <rect
            x={padLeft}
            y={padTop}
            width={plotW}
            height={plotH}
            fill="url(#frontierGrid)"
          />

          {/* Horizontal Grid Lines */}
          {[0.25, 0.5, 0.75, 1.0].map((frac) => {
            const yVal = minProfit + (maxProfit - minProfit) * frac;
            const y = getY(yVal);
            return (
              <g key={frac}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={darkMode ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}
                  strokeDasharray="4 4"
                />
                <text
                  x={padLeft - 10}
                  y={y + 4}
                  textAnchor="end"
                  className="font-mono-tech text-[10px] fill-slate-400 dark:fill-slate-500"
                >
                  &#8377;{Math.round(yVal / 1000)}k
                </text>
              </g>
            );
          })}

          {/* Vertical Grid Lines */}
          {[0.25, 0.5, 0.75, 1.0].map((frac) => {
            const xVal = minRisk + (maxRisk - minRisk) * frac;
            const x = getX(xVal);
            return (
              <g key={frac}>
                <line
                  x1={x}
                  y1={padTop}
                  x2={x}
                  y2={height - padBottom}
                  stroke={darkMode ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}
                  strokeDasharray="4 4"
                />
                <text
                  x={x}
                  y={height - padBottom + 16}
                  textAnchor="middle"
                  className="font-mono-tech text-[10px] fill-slate-400 dark:fill-slate-500"
                >
                  &#8377;{Math.round(xVal / 1000)}k
                </text>
              </g>
            );
          })}

          {/* Axis Labels */}
          <text
            x={width / 2}
            y={height - 12}
            textAnchor="middle"
            className="font-mono-tech text-[10px] uppercase font-bold tracking-widest fill-slate-500"
          >
            Downside Tail Risk (VaR 95% Exposure) &rarr;
          </text>
          <text
            x={-(height / 2)}
            y={22}
            transform="rotate(-90)"
            textAnchor="middle"
            className="font-mono-tech text-[10px] uppercase font-bold tracking-widest fill-slate-500"
          >
            Expected Return (&#8377;/ha) &rarr;
          </text>

          {/* Pareto Efficient Frontier Line */}
          {frontierPath && (
            <path
              d={frontierPath}
              fill="none"
              stroke="#10B981"
              strokeWidth="2.5"
              strokeDasharray="6 3"
              className="drop-shadow-md"
            />
          )}

          {/* Crop Data Nodes */}
          {recommendations.map((crop, idx) => {
            const cx = getX(crop.Downside_Risk ?? 0);
            const cy = getY(crop.Expected_Profit ?? 0);
            const isHovered = hoveredCrop?.Crop === crop.Crop;
            const isPareto = paretoPoints.some((p) => p.Crop === crop.Crop);

            return (
              <g
                key={`${crop.Crop}-${idx}`}
                className="cursor-pointer transition-transform duration-200"
                onMouseEnter={() => setHoveredCrop(crop)}
                onMouseLeave={() => setHoveredCrop(null)}
                onClick={() => onSelectCrop(crop)}
              >
                {/* Outer Glow Halo if Pareto */}
                {isPareto && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHovered ? 18 : 13}
                    fill="#10B981"
                    opacity={darkMode ? 0.25 : 0.18}
                  />
                )}

                {/* Node Circle */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 9 : 7}
                  fill={isPareto ? '#10B981' : darkMode ? '#334155' : '#e2e8f0'}
                  stroke={darkMode ? '#0f172a' : '#ffffff'}
                  strokeWidth="2"
                  className="transition-all duration-200"
                />

                {/* Rank Badge */}
                <text
                  x={cx}
                  y={cy - 12}
                  textAnchor="middle"
                  className="font-mono-tech text-[10px] font-bold fill-slate-700 dark:fill-slate-200 select-none"
                >
                  #{idx + 1} {crop.Crop}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Dynamic Telemetry Tooltip */}
        {hoveredCrop && (
          <div
            className={`absolute top-4 right-4 p-3.5 rounded-xl border shadow-xl backdrop-blur-md z-30 pointer-events-none max-w-xs transition-all ${
              darkMode
                ? 'bg-slate-900/90 border-emerald-500/30 text-white'
                : 'bg-white/95 border-emerald-500/20 text-slate-900'
            }`}
          >
            <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-black/5 dark:border-white/10">
              <AsciiCropGlyph cropName={hoveredCrop.Crop} className="w-6 h-6 text-[7px]" />
              <div>
                <h4 className="font-editorial font-bold text-base leading-tight">
                  {hoveredCrop.Crop}
                </h4>
                <span className="text-[10px] font-mono-tech text-emerald-600 dark:text-emerald-400 font-semibold">
                  {hoveredCrop.Safety_Rating}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[10.5px] font-mono-tech">
              <div>
                <span className="opacity-60 block text-[9px]">EXPECTED PROFIT:</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  &#8377;{Math.round(hoveredCrop.Expected_Profit ?? 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div>
                <span className="opacity-60 block text-[9px]">DOWNSIDE RISK:</span>
                <span className="font-bold text-amber-600 dark:text-amber-400">
                  &#8377;{Math.round(hoveredCrop.Downside_Risk ?? 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div>
                <span className="opacity-60 block text-[9px]">VaR 95% PROFIT:</span>
                <span className={`font-bold ${hoveredCrop.Pessimistic_Profit >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                  &#8377;{Math.round(hoveredCrop.Pessimistic_Profit ?? 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div>
                <span className="opacity-60 block text-[9px]">AG-EFFICIENCY:</span>
                <span className="font-bold">
                  {hoveredCrop.Downside_Risk > 0
                    ? `${(hoveredCrop.Expected_Profit / hoveredCrop.Downside_Risk).toFixed(1)}x`
                    : '3.8x'}
                </span>
              </div>
            </div>

            <div className="mt-2.5 pt-1.5 border-t border-black/5 dark:border-white/10 flex items-center justify-between text-[10px] font-mono-tech text-emerald-600 dark:text-emerald-400">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Click node to view deep analytics
              </span>
              <ArrowUpRight className="w-3 h-3" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
