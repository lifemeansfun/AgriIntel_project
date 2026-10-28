"""N6: Slippage-Tolerant Advisory Quotes.

Mitigates repeated stale-quote rejections and retry storms in concurrent ledger
commitments over high-latency networks by allowing quote admission across ledger
revision increments when profit drift and crop ranking remain within bounded tolerances.

Technical Problem Solved:
Under optimistic concurrency control, when concurrent transactions increment the
global revision counter, pending advisory quotes are invalidated immediately.
This forces repeated client refresh-and-retry cycles. Slippage tolerance admits
commits if marginal profit drift is bounded and the relative ranking of the crop
remains stable.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from modules.regional.economics import finite_number, recommend, scenario_row


class SlippageQuoteEngine:
    """Evaluates and settles advisory quotes with bounded slippage and rank protection."""

    def __init__(self, scenario: dict, quote_validity_seconds: float = 300.0):
        self.scenario = scenario
        self.validity_seconds = quote_validity_seconds
        # Active quotes: quote_id -> quote_dict
        self.quotes: Dict[str, Dict[str, Any]] = {}

    def issue_quote(
        self,
        participant_id: str,
        area_ha: float,
        current_state: dict,
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Issues an advisory quote snapshot tagged with current ledger revision."""
        area = finite_number(area_ha, "area_ha", positive=True)
        now = current_time if current_time is not None else time.time()
        revision = int(current_state.get("revision", 0))

        recs = recommend(self.scenario, current_state, area)

        quote_id = str(uuid4())
        quote_payload = {
            "quote_id": quote_id,
            "participant_id": participant_id,
            "area_ha": area,
            "revision": revision,
            "issued_at": now,
            "expires_at": now + self.validity_seconds,
            "rows": recs,
        }
        self.quotes[quote_id] = quote_payload

        return {
            "quote_id": quote_id,
            "revision": revision,
            "expires_at": quote_payload["expires_at"],
            "recommendations": recs,
        }

    def evaluate_commit_with_slippage(
        self,
        quote_id: str,
        crop: str,
        current_state: dict,
        max_slippage_pct: float = 0.05,  # 5% relative tolerance
        max_abs_slippage: float = 500.0,  # Absolute tolerance (INR) for small/zero profits
        require_rank_stability: bool = True,
        max_rank_drop: int = 0,
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Evaluates whether a quote can execute against the current ledger state."""
        if quote_id not in self.quotes:
            return {
                "accepted": False,
                "reason": "Unknown or expired quote identifier",
                "error_code": "QUOTE_NOT_FOUND",
            }

        quote = self.quotes[quote_id]
        now = current_time if current_time is not None else time.time()

        if now > quote["expires_at"]:
            return {
                "accepted": False,
                "reason": "Quote validity window expired; refresh advice",
                "error_code": "QUOTE_EXPIRED",
            }

        quoted_row = next((r for r in quote["rows"] if r["Crop"] == crop), None)
        if not quoted_row:
            return {
                "accepted": False,
                "reason": f"Crop {crop} not present in original quote",
                "error_code": "INVALID_CROP",
            }

        if not quoted_row.get("Eligible", False):
            return {
                "accepted": False,
                "reason": quoted_row.get("Ineligibility_Reason") or "Crop was ineligible in quote",
                "error_code": "INELIGIBLE_IN_QUOTE",
            }

        area_ha = quote["area_ha"]
        quoted_profit = float(quoted_row["Central_Profit"])

        # Re-evaluate recommendations under CURRENT state
        current_recs = recommend(self.scenario, current_state, area_ha)
        current_row = next((r for r in current_recs if r["Crop"] == crop), None)

        if not current_row or not current_row.get("Eligible", False):
            return {
                "accepted": False,
                "reason": "Capacity for this crop was exhausted by competing commitments",
                "error_code": "CAPACITY_EXHAUSTED",
            }

        current_profit = float(current_row["Central_Profit"])
        abs_slippage = quoted_profit - current_profit

        # Relative slippage calculation guarded against zero or negative denominators
        if abs(quoted_profit) > 10.0:
            rel_slippage = abs_slippage / abs(quoted_profit)
        else:
            rel_slippage = 0.0

        # Accepted if within relative tolerance OR within absolute threshold
        within_tolerance = (rel_slippage <= max_slippage_pct + 1e-9) or (abs_slippage <= max_abs_slippage)

        if not within_tolerance:
            return {
                "accepted": False,
                "reason": (
                    f"Profit slippage ({rel_slippage:.2%}, abs {abs_slippage:,.2f}) "
                    f"exceeds allowed tolerance ({max_slippage_pct:.2%})"
                ),
                "error_code": "EXCESSIVE_SLIPPAGE",
                "quoted_profit": quoted_profit,
                "current_profit": current_profit,
                "slippage_pct": rel_slippage,
                "abs_slippage": abs_slippage,
            }

        # Check rank stability if requested
        eligible_current = [r for r in current_recs if r.get("Eligible", False)]
        eligible_current.sort(key=lambda r: (-r["Score"], r["Crop"]))
        current_rank = next((idx + 1 for idx, r in enumerate(eligible_current) if r["Crop"] == crop), None)

        eligible_quoted = [r for r in quote["rows"] if r.get("Eligible", False)]
        eligible_quoted.sort(key=lambda r: (-r["Score"], r["Crop"]))
        quoted_rank = next((idx + 1 for idx, r in enumerate(eligible_quoted) if r["Crop"] == crop), 1)

        if require_rank_stability and current_rank is not None:
            rank_drop = current_rank - quoted_rank
            if rank_drop > max_rank_drop:
                better_crop = eligible_current[0]["Crop"] if eligible_current else "None"
                return {
                    "accepted": False,
                    "reason": (
                        f"Crop rank dropped from #{quoted_rank} to #{current_rank}; "
                        f"alternative crop {better_crop} is now strictly superior"
                    ),
                    "error_code": "RANK_INSTABILITY",
                    "quoted_rank": quoted_rank,
                    "current_rank": current_rank,
                }

        revisions_drifted = int(current_state.get("revision", 0)) - quote["revision"]

        return {
            "accepted": True,
            "crop": crop,
            "area_ha": area_ha,
            "quoted_profit": quoted_profit,
            "executed_profit": current_profit,
            "profit_drift": current_profit - quoted_profit,
            "slippage_pct": rel_slippage,
            "abs_slippage": abs_slippage,
            "revisions_drifted": revisions_drifted,
            "quoted_rank": quoted_rank,
            "executed_rank": current_rank,
        }
