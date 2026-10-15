"""Seeded classroom policy replay, persisted atomically in the ledger database."""
from contextlib import closing
from copy import deepcopy
import json
import random
from uuid import uuid4

from .economics import evaluate_final, recommend
from .ledger import LedgerError, _json


def empty_state(scenario):
    return {"scenario_id": scenario["id"], "revision": 0,
            "participating_area_ha": scenario["participating_area_ha"],
            "total_committed_area_ha": 0.0, "remaining_area_ha": scenario["participating_area_ha"],
            "commitment": None, "commitments": [],
            "crops": [{"crop": c["crop"], "committed_area_ha": 0.0,
                       "expected_committed_t": 0.0, "conservative_committed_t": 0.0,
                       "outside_supply_t": c["outside_supply_t"], "capacity_t": c["capacity_t"],
                       "remaining_capacity_t": max(0.0, c["capacity_t"] - c["outside_supply_t"]),
                       "remaining_area_ha": min(scenario["participating_area_ha"], max(0.0, c["capacity_t"] - c["outside_supply_t"]) / c["yield_q90"])}
                      for c in scenario["crops"]]}


def _allocate(state, scenario, participant, ranking, area):
    """Use the same hard limits for both policies; a rejected crop can fall through."""
    current = {r["Crop"]: r for r in recommend(scenario, state, area)}
    selected = next((current[c] for c in ranking if c in current and current[c]["Eligible"]), None)
    if selected is None:
        return None, None
    crop = selected["Crop"]
    spec = next(c for c in scenario["crops"] if c["crop"] == crop)
    crop_state = next(c for c in state["crops"] if c["crop"] == crop)
    # Recheck constraints here rather than relying solely on recommendation labels.
    if state["remaining_area_ha"] + 1e-9 < area or crop_state["remaining_capacity_t"] + 1e-9 < area * spec["yield_q90"]:
        raise LedgerError("Replay eligibility disagrees with capacity")
    state["commitments"].append({"id": participant, "participant_id": participant, "crop": crop,
                                 "area_ha": area, "expected_t": area * spec["yield_q50"],
                                 "conservative_t": area * spec["yield_q90"]})
    state["total_committed_area_ha"] += area
    state["remaining_area_ha"] = max(0.0, scenario["participating_area_ha"] - state["total_committed_area_ha"])
    state["revision"] += 1
    crop_state["committed_area_ha"] += area
    crop_state["expected_committed_t"] += area * spec["yield_q50"]
    crop_state["conservative_committed_t"] += area * spec["yield_q90"]
    crop_state["remaining_capacity_t"] = max(0.0, spec["capacity_t"] - spec["outside_supply_t"] - crop_state["conservative_committed_t"])
    for c in state["crops"]:
        cs = next(s for s in scenario["crops"] if s["crop"] == c["crop"])
        c["remaining_area_ha"] = min(state["remaining_area_ha"], c["remaining_capacity_t"] / cs["yield_q90"])
    return crop, selected["Central_Profit"]


class ReplayService:
    def __init__(self, ledger):
        self.ledger = ledger

    def create(self, scenario, seed=42):
        self.ledger.validate_scenario(scenario)
        area = scenario.get("participant_area_ha", 1.0)
        participants = [f"farmer-{i:02d}" for i in range(1, scenario.get("participant_count", 24) + 1)]
        random.Random(seed).shuffle(participants)
        initial = empty_state(scenario)
        body = {"id": str(uuid4()), "seed": seed, "step": 0, "total_steps": len(participants),
                "status": "ready", "scenario": deepcopy(scenario), "participants": participants,
                "static_ranking": [r["Crop"] for r in recommend(scenario, initial, area)],
                "static_state": deepcopy(initial), "dynamic_state": deepcopy(initial),
                "decisions": [], "summary": None,
                "comparison_note": "Both policies use the same capacity limits and final market-price calculation. Participants all cultivate the configured equal area; changing arrival order changes identities, not aggregate demand."}
        with self.ledger.transaction() as db:
            db.execute("INSERT INTO replays VALUES (?,?)", (body["id"], _json(body)))
        return body

    def get(self, replay_id):
        with closing(self.ledger.connect()) as db:
            row = db.execute("SELECT body FROM replays WHERE id=?", (replay_id,)).fetchone()
            if not row:
                raise LedgerError("Unknown replay", 404)
            return json.loads(row["body"])

    def step(self, replay_id):
        with self.ledger.transaction() as db:
            row = db.execute("SELECT body FROM replays WHERE id=?", (replay_id,)).fetchone()
            if not row:
                raise LedgerError("Unknown replay", 404)
            body = json.loads(row["body"])
            if body["status"] == "completed":
                return body
            scenario = body["scenario"]
            participant = body["participants"][body["step"]]
            area = scenario.get("participant_area_ha", 1.0)
            static_crop, static_profit = _allocate(body["static_state"], scenario, participant, body["static_ranking"], area)
            dynamic_ranking = [r["Crop"] for r in recommend(scenario, body["dynamic_state"], area)]
            dynamic_crop, dynamic_profit = _allocate(body["dynamic_state"], scenario, participant, dynamic_ranking, area)
            body["step"] += 1
            body["decisions"].append({"step": body["step"], "participant_id": participant,
                                      "static_crop": static_crop, "dynamic_crop": dynamic_crop,
                                      "static_quote_profit": static_profit, "dynamic_quote_profit": dynamic_profit})
            body["status"] = "completed" if body["step"] == body["total_steps"] else "running"
            if body["status"] == "completed":
                body["summary"] = {"static": evaluate_final(scenario, body["static_state"]),
                                   "dynamic": evaluate_final(scenario, body["dynamic_state"])}
                for policy in ("static", "dynamic"):
                    body["summary"][policy]["rejected_count"] = sum(d[f"{policy}_crop"] is None for d in body["decisions"])
            db.execute("UPDATE replays SET body=? WHERE id=?", (_json(body), replay_id))
            return body
