import React from 'react';
import { ShieldCheck, ShieldAlert, TrendingUp } from '../../components/common/Icons';

export default function RiskBadge({ rating }) {
  if (rating === 'Safe') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
        <ShieldCheck className="w-3.5 h-3.5" /> Low Risk
      </span>
    );
  }

  if (rating === 'High Risk') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
        <ShieldAlert className="w-3.5 h-3.5" /> High Risk
      </span>
    );
  }

  // Default to Moderate Risk
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
      <TrendingUp className="w-3.5 h-3.5" /> Moderate Volatility
    </span>
  );
}
