import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { getScenarios, getScenarioState, createCommitment, cancelCommitment, apiErrorMessage } from '../services/api';

function initialParticipant() {
  try {
    const saved = localStorage.getItem('agriintel_demo_participant');
    if (saved) return saved;
  } catch { /* Browser storage can be unavailable in private contexts. */ }
  return `farmer-${crypto.randomUUID().slice(0, 8)}`;
}
export function useRegionalAdvisory({ formData, setFormData, advisory }) {
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState('');
  const [participantId, setParticipantId] = useState(initialParticipant);
  const [state, setState] = useState(null);
  const [stateError, setStateError] = useState(null);
  const [mutationError, setMutationError] = useState(null);
  const [mutationStatus, setMutationStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [scenarioError, setScenarioError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const { clearRecommendations, fetchRecommendations, result, isFetching } = advisory;
  const pending = useRef(null);
  const mutationBusy = useRef(false);
  const hasRequested = useRef(false);
  const selectedScenario = scenarios.find((item) => item.id === scenarioId) || null;
  const queryKey = JSON.stringify([formData, scenarioId, participantId]);
  const latest = useRef(null);
  useLayoutEffect(() => { latest.current = { queryKey, formData, scenarioId, participantId, advisory: { fetchRecommendations, result, isFetching } }; }, [queryKey, formData, scenarioId, participantId, fetchRecommendations, result, isFetching]);

  useEffect(() => {
    let active = true;
    getScenarios().then((response) => { if (active) setScenarios(response.scenarios || []); }).catch((error) => { if (active) setScenarioError(apiErrorMessage(error)); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    try { localStorage.setItem('agriintel_demo_participant', participantId); } catch { /* Identity remains valid for this tab. */ }
  }, [participantId]);
  useEffect(() => {
    clearRecommendations();
    hasRequested.current = false;
    // oxlint-disable-next-line react/set-state-in-effect -- API state belongs to the complete request identity.
    setState(null);
    setStateError(null);
    setMutationError(null);
    setMutationStatus(null);
  }, [queryKey, clearRecommendations]);

  const fetchAdvice = useCallback(async () => {
    const current = latest.current;
    hasRequested.current = true;
    return current.advisory.fetchRecommendations(current.formData, current.scenarioId ? { scenario_id: current.scenarioId, participant_id: current.participantId.trim() } : {});
  }, []);
  const refreshState = useCallback(async () => {
    const current = latest.current;
    if (!current.scenarioId || !current.participantId.trim()) return null;
    try {
      const response = await getScenarioState(current.scenarioId, current.participantId.trim());
      if (latest.current.queryKey !== current.queryKey) return null;
      setState(response);
      setStateError(null);
      if (hasRequested.current && current.advisory.result && current.advisory.result.revision !== response.revision && !current.advisory.isFetching && !mutationBusy.current) await fetchAdvice();
      return response;
    } catch (error) {
      if (latest.current.queryKey === current.queryKey) setStateError(apiErrorMessage(error));
      return null;
    }
  }, [fetchAdvice]);
  useEffect(() => {
    if (!scenarioId || !participantId.trim()) return undefined;
    let stopped = false;
    let inFlight = false;
    const check = async () => {
      if (stopped || document.visibilityState !== 'visible' || inFlight) return;
      inFlight = true;
      try { await refreshState(); } finally { inFlight = false; }
    };
    check();
    const timer = setInterval(check, 2000);
    window.addEventListener('focus', check);
    document.addEventListener('visibilitychange', check);
    return () => { stopped = true; clearInterval(timer); window.removeEventListener('focus', check); document.removeEventListener('visibilitychange', check); };
  }, [scenarioId, participantId, refreshState]);

  const selectScenario = useCallback((id) => {
    clearRecommendations();
    setScenarioId(id);
    const scenario = scenarios.find((item) => item.id === id);
    if (scenario) setFormData((previous) => ({ ...previous, state: scenario.state, district: scenario.district, season: scenario.season }));
  }, [clearRecommendations, scenarios, setFormData]);
  const updateParticipant = useCallback((id) => { clearRecommendations(); setParticipantId(id); }, [clearRecommendations]);

  const mutate = useCallback(async (kind, crop, retrying = false) => {
    if (mutationBusy.current) return;
    const current = latest.current;
    const commitment = state?.commitment;
    const commitmentId = commitment?.id || commitment?.commitment_id;
    const logicalKey = JSON.stringify([kind, current.scenarioId, current.participantId, kind === 'commit' ? crop : commitmentId]);
    if (pending.current && pending.current.logicalKey !== logicalKey && !retrying) {
      setMutationError('Retry the pending action before starting a different action; its server outcome is not yet known.');
      return;
    }
    if (!pending.current) {
      pending.current = { logicalKey, kind, crop, scenarioId: current.scenarioId, participantId: current.participantId.trim(), idempotencyKey: crypto.randomUUID(), quoteId: current.advisory.result?.quote_id, commitmentId };
      setPendingAction(pending.current);
    }
    const attempt = pending.current;
    mutationBusy.current = true;
    setBusy(true);
    setMutationError(null);
    try {
      const body = { participant_id: attempt.participantId, idempotency_key: attempt.idempotencyKey };
      if (attempt.kind === 'commit') await createCommitment({ ...body, scenario_id: attempt.scenarioId, quote_id: attempt.quoteId, crop: attempt.crop });
      else await cancelCommitment(attempt.commitmentId, body);
      pending.current = null;
      setPendingAction(null);
      if (latest.current.queryKey === current.queryKey) setMutationStatus(kind === 'commit' ? `${crop} planting committed. Shared recommendations are refreshed.` : 'Commitment cancelled and capacity released.');
      await refreshState();
      if (latest.current.queryKey === current.queryKey) await fetchAdvice();
    } catch (error) {
      const status = error?.response?.status;
      const definite = status >= 400 && status < 500;
      if (definite) { pending.current = null; setPendingAction(null); }
      if (latest.current.queryKey === current.queryKey) setMutationError(`${apiErrorMessage(error)}${definite ? '' : ' The outcome is unknown. Retry the same action to safely recover it.'}`);
      if (definite) { await refreshState(); if (latest.current.queryKey === current.queryKey) await fetchAdvice(); }
    } finally {
      mutationBusy.current = false;
      setBusy(false);
    }
  }, [fetchAdvice, refreshState, state]);
  return { scenarios, selectedScenario, scenarioId, selectScenario, participantId, updateParticipant, state, stateError, scenarioError, busy, pendingAction, retryPending: () => pending.current && mutate(pending.current.kind, pending.current.crop, true), mutationError, mutationStatus, fetchAdvice, commit: (crop) => mutate('commit', crop), cancel: () => mutate('cancel') };
}
