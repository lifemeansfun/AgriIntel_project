import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useTheme } from '../../context/useTheme';

export default function UncertaintyChart({
  title,
  data = [],
  color = '#10B981',
  gradientId = 'uncertaintyGrad',
  yAxisUnit = '',
}) {
  const { glassClass, darkMode, textPrimary } = useTheme();

  const gridColor = darkMode ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.05)';
  const axisColor = darkMode ? '#94a3b8' : '#64748b';

  const tooltipStyle = {
    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
    borderColor: darkMode ? '#334155' : '#e2e8f0',
    borderRadius: '12px',
    border: '1px solid',
    color: darkMode ? '#fff' : '#000',
    fontSize: '13px',
  };

  return (
    <div className={`${glassClass} rounded-3xl p-8`}>
      <h3 className={`text-base font-semibold mb-6 ${textPrimary}`}>{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                <stop offset="95%" stopColor={color} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
            <XAxis dataKey="label" stroke={axisColor} fontSize={11} tickLine={false} axisLine={false} />
            <YAxis
              stroke={axisColor}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              unit={yAxisUnit}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color, fontWeight: 'bold' }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={3}
              fill={`url(#${gradientId})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
