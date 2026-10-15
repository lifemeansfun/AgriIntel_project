import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../context/useTheme';
import { createReplay, getReplay, stepReplay, apiErrorMessage } from '../../services/api';
import { formatMoney, formatQuantity } from '../../services/scenarios';

function PolicySummary({ title, state, summary }) {
  const { textSecondary } = useTheme();
  return <div className="rounded-2xl border border-emerald-500/20 p-4 min-w-0"><h3 className="font-semibold mb-3">{title}</h3><div className="flex gap-2 flex-wrap text-xs mb-3">{state?.crops?.map((crop) => <span key={crop.crop} className="bg-emerald-500/10 p-2 rounded-lg">{crop.crop}: <strong>{formatQuantity(crop.committed_area_ha)} ha</strong></span>)}</div><p className={`text-sm ${textSecondary}`}>Committed: {formatQuantity(state?.total_committed_area_ha)} ha · remaining: {formatQuantity(state?.remaining_area_ha)} ha</p>{summary && <dl className="mt-4 text-sm space-y-2">{[['Final scenario profit', summary.total_profit], ['Allocated participant lower tail', summary.lower_tail_mean_profit], ['Unallocated area (ha)', summary.unallocated_area_ha], ['Rejected participants', summary.rejected_count]].map(([label, value]) => <div key={label} className="flex gap-3 justify-between"><dt className={textSecondary}>{label}</dt><dd>{(label.includes('profit') || label.includes('lower tail')) ? formatMoney(value) : formatQuantity(value)}</dd></div>)}</dl>}</div>;
}

export default function ClassroomReplay() {
  const { glassClass, textPrimary, textSecondary, inputClass } = useTheme();
  const [seed, setSeed] = useState('42');
  const [run, setRun] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const busyRef = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const newRun = async () => {
    if (busyRef.current) return;
    const number = Number(seed);
    if (!Number.isSafeInteger(number) || number < 0 || number > 2147483647) { setError('Enter a whole-number seed from 0 to 2147483647.'); return; }
    setPlaying(false); busyRef.current = true; setBusy(true); setError(null);
    try { const data = await createReplay(number); if (mounted.current) setRun(data); }
    catch (err) { if (mounted.current) setError(apiErrorMessage(err)); }
    finally { busyRef.current = false; if (mounted.current) setBusy(false); }
  };
  const advance = async () => {
    if (busyRef.current || !run || run.status === 'completed') return;
    busyRef.current = true; setBusy(true); setError(null);
    try { const data = await stepReplay(run.id); if (mounted.current) { setRun(data); if (data.status === 'completed') setPlaying(false); } }
    catch (err) {
      if (mounted.current) { setPlaying(false); setError(`${apiErrorMessage(err)} Replay paused; checking its saved step before retry.`); }
      try { const current = await getReplay(run.id); if (mounted.current) setRun(current); } catch { /* Keep the last known step and the explicit error. */ }
    } finally { busyRef.current = false; if (mounted.current) setBusy(false); }
  };
  useEffect(() => {
    if (!playing || busy || !run || run.status === 'completed') return undefined;
    const timer = setTimeout(() => { if (document.visibilityState === 'visible') advance(); else setPlaying(false); }, 650);
    return () => clearTimeout(timer);
  });
  return <section className={`${glassClass} max-w-5xl w-full mx-auto rounded-3xl p-5 sm:p-7 mt-8 mb-10 ${textPrimary}`} aria-label="Classroom replay"><p className="text-xs uppercase tracking-widest font-mono-tech text-emerald-700 dark:text-emerald-300">Seeded classroom replay</p><h2 className="font-editorial text-3xl font-bold mt-2">Watch recommendations respond</h2><p className={`text-sm leading-relaxed mt-3 max-w-3xl ${textSecondary}`}>24 simulated farmers choose one hectare each. Static ranking keeps its initial order; supply-aware ranking updates after every commitment. Both policies use identical forecasts, arrival order, price rules and capacity limits. Because participants have equal areas, changing the seed changes identities rather than aggregate demand. Each run has its own ledger.</p><div className="flex items-end flex-wrap gap-3 mt-5"><div><label htmlFor="replay-seed" className={`block text-xs mb-2 ${textSecondary}`}>Arrival-order seed</label><input id="replay-seed" type="number" min="0" max="2147483647" step="1" value={seed} onChange={(event) => setSeed(event.target.value)} className={`${inputClass} border rounded-xl px-3 py-2 w-36`} /></div><button type="button" disabled={busy} onClick={newRun} className="rounded-xl bg-emerald-700 text-white px-4 py-2.5 font-semibold text-sm disabled:opacity-50">{run ? 'New isolated run' : 'Start replay'}</button>{run && <><button type="button" disabled={busy || playing || run.status === 'completed'} onClick={advance} className="rounded-xl border border-emerald-600 px-4 py-2 text-sm disabled:opacity-50">Step one farmer</button><button type="button" disabled={run.status === 'completed'} onClick={() => setPlaying((value) => !value)} className="rounded-xl border border-emerald-600 px-4 py-2 text-sm disabled:opacity-50">{playing ? 'Pause' : 'Play'}</button><span className={`text-xs ${textSecondary}`} aria-live="polite">Step {run.step} / {run.total_steps} · seed {run.seed}{run.status === 'completed' ? ' · completed' : ''}</span></>}</div>{error && <p role="alert" className="mt-4 text-sm text-rose-600 dark:text-rose-300">{error}</p>}{run && <><div className="grid md:grid-cols-2 gap-4 mt-6"><PolicySummary title="Static ranking" state={run.static_state} summary={run.summary?.static} /><PolicySummary title="Supply-aware ranking" state={run.dynamic_state} summary={run.summary?.dynamic} /></div><p className={`text-xs leading-relaxed mt-4 ${textSecondary}`}>Reported profit evaluates the final allocation at a common modeled market price. The lower-tail mean covers the lowest 10% of allocated participants; rejected farmers are reported separately. Quoted profits are scenarios, not guaranteed sale proceeds. A replay demonstrates the specified simulation, not a measured farmer-income improvement.</p>{run.decisions?.length > 0 && <details className="mt-5"><summary className="text-sm font-semibold cursor-pointer">Recent choices</summary><div className="overflow-x-auto mt-3"><table className="w-full text-sm text-left"><thead><tr>{['Farmer', 'Static choice', 'Supply-aware choice'].map((label) => <th className="py-2 pr-4" key={label}>{label}</th>)}</tr></thead><tbody>{run.decisions.slice(-6).map((decision) => <tr key={decision.step}><td className="py-2 pr-4">{decision.step}</td><td className="py-2 pr-4">{decision.static_crop || 'Unallocated'}</td><td className="py-2 pr-4">{decision.dynamic_crop || 'Unallocated'}</td></tr>)}</tbody></table></div></details>}</>}</section>;
}
