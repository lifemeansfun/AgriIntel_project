import { useTheme } from '../../context/useTheme';
import { formatMoney, formatQuantity } from '../../services/scenarios';

export default function CandidateGallery({ candidates = [], onSelect, activeCrop }) {
  const { glassClass, textPrimary, textSecondary } = useTheme();
  if (!candidates.length) return null;
  return <section className="w-full max-w-5xl mx-auto mt-8"><h3 className={`text-sm font-semibold mb-4 ${textPrimary}`}>Compare crop scenarios</h3><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{candidates.map((crop, index) => <button type="button" key={crop.Crop} onClick={() => onSelect(crop)} aria-pressed={activeCrop?.Crop === crop.Crop} className={`${glassClass} rounded-2xl p-5 text-left border ${activeCrop?.Crop === crop.Crop ? 'ring-2 ring-emerald-500' : ''} ${textPrimary}`}><p className={`font-mono-tech text-xs ${textSecondary}`}>Rank {index + 1} · {crop.Eligible ? 'Available' : 'Unavailable'}</p><h4 className="font-editorial font-bold text-2xl mt-2 mb-4">{crop.Crop}</h4><dl className="space-y-2 text-sm">{[['Central profit', formatMoney(crop.Central_Profit)], ['Pessimistic profit', formatMoney(crop.Pessimistic_Profit)], ['Median yield', `${formatQuantity(crop.Yield_q50, 2)} t/ha`]].map(([label, value]) => <div className="flex gap-2 justify-between" key={label}><dt className={textSecondary}>{label}</dt><dd>{value}</dd></div>)}</dl></button>)}</div></section>;
}
