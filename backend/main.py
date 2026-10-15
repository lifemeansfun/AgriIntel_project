"""AgriIntel API: historical browsing and transactional classroom supply feedback.

Importing this module creates routes only. Data and durable storage are opened by
lifespan, and both are injectable for isolated tests and reproducible demonstrations.
"""
from contextlib import asynccontextmanager
import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from modules.regional.catalog import Catalog, CatalogUnavailableError
from modules.regional.economics import recommend
from modules.regional.ledger import LedgerError, RegionalLedger
from modules.regional.replay import ReplayService

ROOT = Path(__file__).resolve().parents[1]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RecommendationRequest(StrictModel):
    state: Identifier
    district: Identifier
    season: Identifier
    area_hectares: float = Field(default=1.0, gt=0, le=1_000_000, strict=True)
    scenario_id: Identifier | None = None
    participant_id: Identifier | None = None


class CommitRequest(StrictModel):
    scenario_id: Identifier
    participant_id: Identifier
    quote_id: Identifier
    crop: Identifier
    idempotency_key: Identifier


class CancelRequest(StrictModel):
    participant_id: Identifier
    idempotency_key: Identifier


class ReplayRequest(StrictModel):
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


def create_app(*, db_path=None, active_path=None, catalog=None, clock=None):
    @asynccontextmanager
    async def lifespan(application):
        try:
            application.state.catalog = catalog if catalog is not None else Catalog(active_path)
            application.state.catalog_error = None
        except CatalogUnavailableError:
            application.state.catalog = None
            application.state.catalog_error = "Validated historical artifact unavailable. Generate and activate a repaired run."
        path = db_path or os.environ.get("AGRIINTEL_DB_PATH") or ROOT / "data" / "api_processed" / "regional.sqlite3"
        kwargs = {"clock": clock} if clock is not None else {}
        application.state.ledger = RegionalLedger(path, **kwargs)
        for scenario in application.state.catalog.scenarios() if application.state.catalog is not None else []:
            application.state.ledger.ensure_scenario(scenario)
        application.state.replays = ReplayService(application.state.ledger)
        yield

    application = FastAPI(title="AgriIntel API", version="2.0", lifespan=lifespan)
    application.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                               allow_methods=["*"], allow_headers=["*"])
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    @application.exception_handler(LedgerError)
    async def ledger_error(_request, error):
        return JSONResponse(status_code=error.status, content={"detail": str(error)})

    @application.middleware("http")
    async def no_stale_state(request: Request, call_next):
        path = request.url.path.rstrip("/")
        # Durable acknowledgement recovery must remain available when a forecast
        # artifact is retired or temporarily unavailable. These routes consult
        # only the persisted scenario, quote and idempotency records.
        recovery_route = (request.method == "GET" and path == "/api/v2/state") or (
            request.method == "POST" and (path == "/api/v2/commitments" or
                re.fullmatch(r"/api/v2/commitments/[^/]+/cancel", path) is not None))
        if application.state.catalog is None and not recovery_route:
            return JSONResponse(status_code=503, content={"detail": application.state.catalog_error}, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def metadata():
        return application.state.catalog.metadata

    def lookup_scenario(scenario_id):
        try:
            return application.state.catalog.scenario(scenario_id)
        except KeyError:
            raise HTTPException(404, "Unknown or unavailable scenario") from None

    def recommendation_response(req):
        cat = application.state.catalog
        meta = metadata()
        if not req.scenario_id:
            rows = cat.historical_rows(req.state, req.district, req.season, req.area_hectares)
            if not rows:
                raise HTTPException(404, "No supported historical data for this location and season")
            return {**meta, "recommendations": rows, "mode": "historical",
                    "scenario_id": None, "revision": None, "quote_id": None, "quote_expires_at": None}
        if not req.participant_id:
            raise HTTPException(422, "Feedback recommendations require a participant_id")
        scenario = lookup_scenario(req.scenario_id)
        if (req.state, req.district, req.season) != (scenario["state"], scenario["district"], scenario["season"]):
            raise HTTPException(422, "Selected location does not match the scenario")
        state = application.state.ledger.state(req.scenario_id, req.participant_id)
        rows = recommend(scenario, state, req.area_hectares)
        if state["commitment"]:
            for row in rows:
                row["Eligible"] = False
                row["Ineligibility_Reason"] = "Cancel the existing commitment before changing crop"
        quote = application.state.ledger.issue_quote(req.scenario_id, req.participant_id,
                                                    req.area_hectares, state["revision"], rows)
        return {**meta, "recommendations": rows, "mode": "feedback",
                "scenario_id": req.scenario_id, "revision": state["revision"], **quote}

    @application.get("/")
    def root():
        cat = application.state.catalog
        return {"status": "AgriIntel API is running", "api_version": 2,
                "cached_locations": len(cat.locations), "data": metadata()}

    @application.get("/api/v2/locations")
    def locations():
        return {"locations": application.state.catalog.locations, **metadata()}

    @application.get("/api/v2/scenarios")
    def scenarios():
        return {"scenarios": application.state.catalog.scenarios(), **metadata()}

    @application.post("/api/v2/recommendations")
    def recommendations(req: RecommendationRequest):
        return recommendation_response(req)

    @application.get("/api/v2/state")
    def state(scenario_id: Identifier, participant_id: Identifier | None = None):
        return application.state.ledger.state(scenario_id, participant_id)

    @application.post("/api/v2/commitments")
    def commit(req: CommitRequest):
        return application.state.ledger.commit(req.scenario_id, req.participant_id, req.quote_id,
                                               req.crop, req.idempotency_key)

    @application.post("/api/v2/commitments/{commitment_id}/cancel")
    def cancel(commitment_id: Identifier, req: CancelRequest):
        return application.state.ledger.cancel(commitment_id, req.participant_id, req.idempotency_key)

    @application.post("/api/v2/replays")
    def new_replay(req: ReplayRequest):
        available = application.state.catalog.scenarios()
        if not available:
            raise HTTPException(503, "No supported feedback scenario is available")
        return application.state.replays.create(available[0], req.seed)

    @application.get("/api/v2/replays/{replay_id}")
    def replay(replay_id: Identifier):
        return application.state.replays.get(replay_id)

    @application.post("/api/v2/replays/{replay_id}/step")
    def step_replay(replay_id: Identifier):
        return application.state.replays.step(replay_id)

    @application.get("/api/locations", deprecated=True)
    def legacy_locations():
        return application.state.catalog.locations

    @application.post("/api/recommendations", deprecated=True)
    def legacy_recommendations(req: RecommendationRequest):
        # Compatibility is limited to historical browsing; v1 cannot create quotes.
        return recommendation_response(req.model_copy(update={"scenario_id": None, "participant_id": None}))

    @application.get("/api/recommendations", deprecated=True)
    def legacy_recommendations_get(state: Identifier, district: Identifier, season: Identifier,
                                   area_hectares: float = Query(1.0, gt=0, le=1_000_000, allow_inf_nan=False)):
        return recommendation_response(RecommendationRequest(state=state, district=district, season=season,
                                                               area_hectares=area_hectares))

    @application.post("/api/commit", deprecated=True)
    def retired_commit():
        raise HTTPException(410, "Unscoped commitments are retired. Use /api/v2/recommendations and /api/v2/commitments.")

    @application.get("/api/state", deprecated=True)
    def retired_state():
        raise HTTPException(410, "Unscoped state is retired. Use /api/v2/state with scenario_id.")

    return application


app = create_app()
