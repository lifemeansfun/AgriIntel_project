"""Transactional regional planting ledger. Construction is explicit and never imports legacy logs."""
from __future__ import annotations

from contextlib import closing, contextmanager
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Callable
from uuid import uuid4


class LedgerError(ValueError):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def finite_positive(value: float, name: str = "area") -> float:
    if isinstance(value, bool):
        raise LedgerError(f"{name} must be finite and positive", 422)
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"{name} must be finite and positive", 422) from exc
    if not math.isfinite(value) or value <= 0:
        raise LedgerError(f"{name} must be finite and positive", 422)
    return value


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class RegionalLedger:
    def __init__(self, path: str | Path, clock: Callable[[], float] = time.time):
        self.path = str(path)
        self.clock = clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY, config TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS commitments (
                    id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES scenarios(id),
                    participant_id TEXT NOT NULL, crop TEXT NOT NULL, area_ha REAL NOT NULL CHECK(area_ha>0),
                    expected_t REAL NOT NULL CHECK(expected_t>=0), conservative_t REAL NOT NULL CHECK(conservative_t>=0),
                    created_at REAL NOT NULL, cancelled_at REAL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_participant
                    ON commitments(scenario_id,participant_id) WHERE cancelled_at IS NULL;
                CREATE TABLE IF NOT EXISTS quotes (
                    id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES scenarios(id),
                    participant_id TEXT NOT NULL, revision INTEGER NOT NULL, area_ha REAL NOT NULL,
                    rows_json TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    scope TEXT NOT NULL, key TEXT NOT NULL, fingerprint TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY(scope,key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id TEXT NOT NULL REFERENCES scenarios(id),
                    revision INTEGER NOT NULL, kind TEXT NOT NULL, commitment_id TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at REAL NOT NULL,
                    UNIQUE(scenario_id,revision)
                );
                CREATE TABLE IF NOT EXISTS replays (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def validate_scenario(scenario):
        try:
            if not scenario["id"] or not scenario["crops"]:
                raise ValueError("Scenario requires an identifier and crops")
            finite_positive(scenario["participating_area_ha"], "Participating area")
            if "participant_area_ha" in scenario:
                finite_positive(scenario["participant_area_ha"], "Participant area")
            if "participant_count" in scenario and (isinstance(scenario["participant_count"], bool) or
                    not isinstance(scenario["participant_count"], int) or scenario["participant_count"] <= 0):
                raise ValueError("Participant count must be a positive integer")
            names = set()
            for crop in scenario["crops"]:
                if not crop["crop"] or crop["crop"] in names:
                    raise ValueError("Crop names must be unique and nonempty")
                names.add(crop["crop"])
                for key in ("yield_q50", "yield_q90", "reference_price", "reference_supply_t", "capacity_t", "theta"):
                    finite_positive(crop[key], key)
                for key in ("yield_q10", "cost_per_ha", "outside_supply_t", "phi"):
                    if isinstance(crop[key], bool) or not math.isfinite(float(crop[key])):
                        raise ValueError(f"{key} must be finite")
                if not 0 <= crop["yield_q10"] <= crop["yield_q50"] <= crop["yield_q90"]:
                    raise ValueError("Yield estimates must be nonnegative and ordered")
                if crop["cost_per_ha"] < 0 or not 0 <= crop["outside_supply_t"] <= crop["capacity_t"]:
                    raise ValueError("Cost and outside supply must be nonnegative and outside supply cannot exceed capacity")
                if crop["phi"] >= 0 or not 0 < crop["theta"] <= 1:
                    raise ValueError("Supply response requires negative phi and theta in (0, 1]")
        except (KeyError, TypeError, ValueError) as exc:
            raise LedgerError(f"Invalid scenario configuration: {exc}", 422) from exc

    def ensure_scenario(self, scenario: dict):
        self.validate_scenario(scenario)
        config = _json(scenario)
        with self.transaction() as db:
            existing = db.execute("SELECT config FROM scenarios WHERE id=?", (scenario["id"],)).fetchone()
            if existing and existing["config"] != config:
                raise LedgerError("Scenario configuration changed; create a new scenario identifier")
            db.execute("INSERT OR IGNORE INTO scenarios(id,config) VALUES (?,?)", (scenario["id"], config))

    def _scenario(self, db, scenario_id):
        found = db.execute("SELECT config,revision FROM scenarios WHERE id=?", (scenario_id,)).fetchone()
        if not found:
            raise LedgerError("Unknown scenario", 404)
        return json.loads(found["config"]), found["revision"]

    def scenario(self, scenario_id):
        with closing(self.connect()) as db:
            return self._scenario(db, scenario_id)[0]

    def _state(self, db, scenario_id, participant_id=None):
        config, revision = self._scenario(db, scenario_id)
        rows = db.execute("SELECT * FROM commitments WHERE scenario_id=? AND cancelled_at IS NULL", (scenario_id,)).fetchall()
        total_area = sum(r["area_ha"] for r in rows)
        remaining_area = max(0.0, config["participating_area_ha"] - total_area)
        crops = []
        for crop in config["crops"]:
            selected = [r for r in rows if r["crop"] == crop["crop"]]
            expected = sum(r["expected_t"] for r in selected)
            conservative = sum(r["conservative_t"] for r in selected)
            headroom = max(0.0, crop["capacity_t"] - crop["outside_supply_t"] - conservative)
            crops.append({"crop": crop["crop"], "committed_area_ha": sum(r["area_ha"] for r in selected),
                          "expected_committed_t": expected, "conservative_committed_t": conservative,
                          "outside_supply_t": crop["outside_supply_t"], "capacity_t": crop["capacity_t"],
                          "remaining_capacity_t": headroom,
                          "remaining_area_ha": min(remaining_area, headroom / crop["yield_q90"])})
        own = next((dict(r) for r in rows if r["participant_id"] == participant_id), None)
        return {"scenario_id": scenario_id, "revision": revision,
                "participating_area_ha": config["participating_area_ha"],
                "total_committed_area_ha": total_area, "remaining_area_ha": remaining_area,
                "crops": crops, "commitment": own, "commitments": [dict(r) for r in rows]}

    def state(self, scenario_id, participant_id=None):
        with closing(self.connect()) as db:
            # A read transaction holds one consistent snapshot for the revision and sums.
            db.execute("BEGIN")
            return self._state(db, scenario_id, participant_id)

    def issue_quote(self, scenario_id, participant_id, area_ha, revision, rows):
        area_ha = finite_positive(area_ha)
        with self.transaction() as db:
            _, actual = self._scenario(db, scenario_id)
            if actual != revision:
                raise LedgerError("Scenario changed while quoting; refresh advice")
            quote_id, expires = str(uuid4()), self.clock() + 300
            db.execute("INSERT INTO quotes VALUES (?,?,?,?,?,?,?)",
                       (quote_id, scenario_id, participant_id, revision, area_ha, _json(rows), expires))
        return {"quote_id": quote_id, "quote_expires_at": expires}

    def _cached(self, db, scope, key, fingerprint):
        row = db.execute("SELECT fingerprint,response FROM requests WHERE scope=? AND key=?", (scope, key)).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise LedgerError("Idempotency key was already used with different input")
            return json.loads(row["response"])
        return None

    def _remember(self, db, scope, key, fingerprint, response):
        db.execute("INSERT INTO requests VALUES (?,?,?,?)", (scope, key, fingerprint, _json(response)))

    def commit(self, scenario_id, participant_id, quote_id, crop, idempotency_key):
        scope = _json(["commit", scenario_id, participant_id])
        fingerprint = sha256(_json([scenario_id, participant_id, quote_id, crop]).encode()).hexdigest()
        with self.transaction() as db:
            cached = self._cached(db, scope, idempotency_key, fingerprint)
            if cached is not None:
                return cached
            config, revision = self._scenario(db, scenario_id)
            quote = db.execute("SELECT * FROM quotes WHERE id=?", (quote_id,)).fetchone()
            if not quote or quote["scenario_id"] != scenario_id or quote["participant_id"] != participant_id:
                raise LedgerError("Quote is not valid for this participant and scenario")
            if self.clock() >= quote["expires_at"]:
                raise LedgerError("Quote expired; refresh advice")
            if quote["revision"] != revision:
                raise LedgerError("Quote is stale; refresh advice")
            if db.execute("SELECT 1 FROM commitments WHERE scenario_id=? AND participant_id=? AND cancelled_at IS NULL",
                          (scenario_id, participant_id)).fetchone():
                raise LedgerError("Participant already has an active commitment; cancel it first")
            crop_config = next((c for c in config["crops"] if c["crop"] == crop), None)
            quoted = next((r for r in json.loads(quote["rows_json"]) if r["Crop"] == crop), None)
            if crop_config is None or quoted is None:
                raise LedgerError("Crop is not supported by this quote", 422)
            if not quoted.get("Eligible", False):
                raise LedgerError(quoted.get("Ineligibility_Reason") or "Crop is ineligible")
            state = self._state(db, scenario_id, participant_id)
            crop_state = next(c for c in state["crops"] if c["crop"] == crop)
            area = finite_positive(quote["area_ha"])
            expected = area * finite_positive(crop_config["yield_q50"], "Median yield")
            conservative = area * finite_positive(crop_config["yield_q90"], "Upper yield")
            if area > state["remaining_area_ha"] + 1e-9 or conservative > crop_state["remaining_capacity_t"] + 1e-9:
                raise LedgerError("Capacity exhausted; refresh advice")
            commitment_id, now = str(uuid4()), self.clock()
            db.execute("INSERT INTO commitments VALUES (?,?,?,?,?,?,?,?,NULL)",
                       (commitment_id, scenario_id, participant_id, crop, area, expected, conservative, now))
            db.execute("UPDATE scenarios SET revision=revision+1 WHERE id=?", (scenario_id,))
            db.execute("INSERT INTO events(scenario_id,revision,kind,commitment_id,payload,created_at) VALUES (?,?,?,?,?,?)",
                       (scenario_id, revision + 1, "COMMIT", commitment_id,
                        _json({"participant_id": participant_id, "crop": crop, "area_ha": area,
                               "expected_t": expected, "conservative_t": conservative}), now))
            response = {"commitment_id": commitment_id, "revision": revision + 1,
                        "state": self._state(db, scenario_id, participant_id)}
            self._remember(db, scope, idempotency_key, fingerprint, response)
            return response

    def cancel(self, commitment_id, participant_id, idempotency_key):
        scope = _json(["cancel", commitment_id, participant_id])
        fingerprint = sha256(_json([commitment_id, participant_id]).encode()).hexdigest()
        with self.transaction() as db:
            cached = self._cached(db, scope, idempotency_key, fingerprint)
            if cached is not None:
                return cached
            found = db.execute("SELECT * FROM commitments WHERE id=?", (commitment_id,)).fetchone()
            if not found:
                raise LedgerError("Unknown commitment", 404)
            if found["participant_id"] != participant_id:
                raise LedgerError("Commitment belongs to another participant", 403)
            scenario_id = found["scenario_id"]
            if found["cancelled_at"] is None:
                now = self.clock()
                db.execute("UPDATE commitments SET cancelled_at=? WHERE id=?", (now, commitment_id))
                db.execute("UPDATE scenarios SET revision=revision+1 WHERE id=?", (scenario_id,))
                _, revision = self._scenario(db, scenario_id)
                db.execute("INSERT INTO events(scenario_id,revision,kind,commitment_id,payload,created_at) VALUES (?,?,?,?,?,?)",
                           (scenario_id, revision, "CANCEL", commitment_id,
                            _json({"released_area_ha": found["area_ha"], "released_expected_t": found["expected_t"],
                                   "released_conservative_t": found["conservative_t"]}), now))
            state = self._state(db, scenario_id, participant_id)
            response = {"commitment_id": commitment_id, "revision": state["revision"], "state": state}
            self._remember(db, scope, idempotency_key, fingerprint, response)
            return response
