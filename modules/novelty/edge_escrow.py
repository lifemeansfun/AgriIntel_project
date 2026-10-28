"""N4: Escrowed Capacity Tokens for Offline Edge Commitment.

Enables offline village extension kiosks and mobile field devices to accept farmer
commitments locally without continuous network connectivity, guaranteeing zero
commitment-budget oversubscription relative to the centrally issued capacity ceiling.

Note: This protocol guarantees that admitted commitments do not exceed the sum of
centrally allocated token quotas under the stated cryptographic protocol assumptions.
It does not guarantee that realized physical harvest remains below the market-capacity
estimate (which is subject to real-world agronomic and weather volatility).
"""
from __future__ import annotations

from enum import Enum
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from modules.regional.economics import finite_number


class TokenState(str, Enum):
    ISSUED = "ISSUED"
    ACTIVE_OFFLINE = "ACTIVE_OFFLINE"
    SUBMITTED = "SUBMITTED"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _compute_entry_mac(kiosk_key: bytes, prev_hash: str, payload: dict) -> str:
    message = f"{prev_hash}:{_canonical_json(payload)}".encode("utf-8")
    return hmac.new(kiosk_key, message, hashlib.sha256).hexdigest()


class EdgeKioskNode:
    """Offline Edge Device (e.g. tablet or kiosk) managing local commitments."""

    def __init__(self, kiosk_id: str, device_key: Optional[str] = None):
        self.kiosk_id = kiosk_id
        self.device_key = (
            device_key.encode("utf-8")
            if device_key
            else f"dev-key-{kiosk_id}-32b-secret".encode("utf-8")
        )
        self.active_token: Optional[Dict[str, Any]] = None
        self.remaining_escrow_t: float = 0.0
        self.commitments: List[Dict[str, Any]] = []
        self.current_hash: Optional[str] = None
        self.is_connected: bool = False

    def load_escrow_token(self, token: Dict[str, Any]) -> None:
        """Loads a newly issued signed capacity escrow token from the server."""
        if token.get("kiosk_id") != self.kiosk_id:
            raise ValueError(f"Token kiosk_id ({token.get('kiosk_id')}) does not match node id ({self.kiosk_id})")

        self.active_token = dict(token)
        self.remaining_escrow_t = float(token["allocated_capacity_t"])
        self.commitments = []
        # Chain head H_0 is cryptographically bound to the device key and token id:
        # H_0 = HMAC_device_key(token_id)
        self.current_hash = hmac.new(
            self.device_key, token["token_id"].encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self.is_connected = False

    def commit_offline(
        self,
        farmer_id: str,
        area_ha: float,
        yield_q90: float,
        commitment_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Atomically accepts an offline commitment against the local escrow quota."""
        if not self.active_token:
            raise RuntimeError("No active escrow token loaded on edge node")

        area = finite_number(area_ha, "area_ha", positive=True)
        q90 = finite_number(yield_q90, "yield_q90", positive=True)
        required_t = area * q90

        if required_t > self.remaining_escrow_t + 1e-9:
            raise ValueError(
                f"Required capacity {required_t:.2f}t exceeds remaining local escrow {self.remaining_escrow_t:.2f}t"
            )

        ts = timestamp if timestamp is not None else time.time()
        if ts > self.active_token["expires_at"]:
            raise ValueError("Active escrow token has expired; offline admission halted")

        seq = len(self.commitments) + 1
        cid = commitment_id or str(uuid4())

        payload = {
            "seq": seq,
            "commitment_id": cid,
            "farmer_id": farmer_id,
            "crop": self.active_token["crop"],
            "area_ha": area,
            "required_capacity_t": required_t,
            "timestamp": ts,
        }

        # Update authenticated hash chain: H_t = HMAC_device_key(H_{t-1} : payload)
        self.current_hash = _compute_entry_mac(self.device_key, self.current_hash, payload)
        payload["hash"] = self.current_hash

        self.remaining_escrow_t = max(0.0, self.remaining_escrow_t - required_t)
        self.commitments.append(payload)

        return {
            "status": "accepted_offline",
            "kiosk_id": self.kiosk_id,
            "token_id": self.active_token["token_id"],
            "commitment": payload,
            "remaining_local_escrow_t": self.remaining_escrow_t,
        }

    def export_sync_payload(self) -> Dict[str, Any]:
        """Packages the authenticated hash-chained log for upload to central ledger."""
        if not self.active_token:
            raise RuntimeError("No active token to export")

        return {
            "kiosk_id": self.kiosk_id,
            "token": dict(self.active_token),
            "commitments": [dict(c) for c in self.commitments],
            "final_hash": self.current_hash,
            "unused_escrow_t": self.remaining_escrow_t,
        }


class EdgeEscrowManager:
    """Central Authority managing cryptographically signed escrow tokens and reconciliation."""

    def __init__(
        self,
        server_secret_key: str = "agriintel-server-master-secret-key-64b",
        kiosk_registry: Optional[Dict[str, str]] = None,
    ):
        self.server_secret_key = server_secret_key.encode("utf-8")
        # Registered kiosks and their shared/public device keys
        self.kiosk_registry: Dict[str, bytes] = {}
        if kiosk_registry:
            for kid, kkey in kiosk_registry.items():
                self.kiosk_registry[kid] = kkey.encode("utf-8")

        # Global token store: token_id -> dict
        self.tokens: Dict[str, Dict[str, Any]] = {}
        # Settled commitment IDs for global deduplication
        self.settled_commitment_ids: set[str] = set()
        # Settled commitments log
        self.settled_commitments: List[Dict[str, Any]] = []
        # Settlement cache for idempotency: token_id -> response_dict
        self.settlement_cache: Dict[str, Dict[str, Any]] = {}
        # Kiosk historical statistics
        self.kiosk_stats: Dict[str, Dict[str, float]] = {}

    def register_kiosk(self, kiosk_id: str, device_key: str) -> None:
        """Registers a trusted kiosk device and its credential."""
        self.kiosk_registry[kiosk_id] = device_key.encode("utf-8")

    def _get_kiosk_key(self, kiosk_id: str) -> bytes:
        if kiosk_id in self.kiosk_registry:
            return self.kiosk_registry[kiosk_id]
        # Deterministic default device key fallback for self-registered nodes
        return f"dev-key-{kiosk_id}-32b-secret".encode("utf-8")

    def _sign_token(self, payload: dict) -> str:
        body = _canonical_json(payload).encode("utf-8")
        return hmac.new(self.server_secret_key, body, hashlib.sha256).hexdigest()

    def issue_escrow_token(
        self,
        kiosk_id: str,
        scenario_id: str,
        crop: str,
        capacity_t: float,
        validity_seconds: float = 86400.0,  # 24 hours
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Issues an authenticated, cryptographically signed capacity token."""
        cap = finite_number(capacity_t, "capacity_t", positive=True)
        now = current_time if current_time is not None else time.time()
        token_id = str(uuid4())

        token_body = {
            "token_id": token_id,
            "kiosk_id": kiosk_id,
            "scenario_id": scenario_id,
            "crop": crop,
            "allocated_capacity_t": cap,
            "issued_at": now,
            "expires_at": now + validity_seconds,
            "state": TokenState.ISSUED.value,
        }
        token_body["signature"] = self._sign_token(token_body)
        self.tokens[token_id] = token_body
        return dict(token_body)

    def verify_token(self, token: Dict[str, Any]) -> bool:
        """Verifies HMAC signature and schema of a capacity token."""
        if "signature" not in token:
            return False
        expected_sig = token["signature"]
        body = {k: v for k, v in token.items() if k != "signature"}
        computed_sig = self._sign_token(body)
        return hmac.compare_digest(expected_sig, computed_sig)

    def expire_token(self, token_id: str) -> Dict[str, Any]:
        """Marks an unsettled token as expired and reclaims its capacity centrally."""
        if token_id not in self.tokens:
            raise ValueError(f"Token {token_id} not found")
        tok = self.tokens[token_id]
        if tok["state"] == TokenState.SETTLED.value:
            raise ValueError(f"Cannot expire settled token {token_id}")
        tok["state"] = TokenState.EXPIRED.value
        return {"token_id": token_id, "state": TokenState.EXPIRED.value}

    def revoke_token(self, token_id: str, reason: str = "security_revocation") -> Dict[str, Any]:
        """Revokes an unsettled token due to security compromise or operator intervention."""
        if token_id not in self.tokens:
            raise ValueError(f"Token {token_id} not found")
        tok = self.tokens[token_id]
        if tok["state"] == TokenState.SETTLED.value:
            raise ValueError(f"Cannot revoke settled token {token_id}")
        tok["state"] = TokenState.REJECTED.value
        tok["revocation_reason"] = reason
        return {"token_id": token_id, "state": TokenState.REJECTED.value, "reason": reason}

    def reconcile_and_settle(
        self,
        sync_payload: Dict[str, Any],
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validates the uploaded offline hash chain and reconciles central capacity idempotently."""
        token = sync_payload.get("token")
        commitments = sync_payload.get("commitments", [])
        claimed_final_hash = sync_payload.get("final_hash")

        if not token or not self.verify_token(token):
            raise ValueError("Invalid or forged escrow token signature")

        token_id = token["token_id"]
        token_kiosk_id = token["kiosk_id"]
        submitting_kiosk_id = sync_payload.get("kiosk_id", token_kiosk_id)

        if submitting_kiosk_id != token_kiosk_id:
            raise ValueError(
                f"Token kiosk_id mismatch: token registered to {token_kiosk_id}, submitted by {submitting_kiosk_id}"
            )

        kiosk_id = token_kiosk_id

        # Check idempotent cache
        if token_id in self.settlement_cache:
            return self.settlement_cache[token_id]

        if token_id not in self.tokens:
            raise ValueError(f"Token {token_id} is unknown to central authority")

        stored_token = self.tokens[token_id]
        if stored_token["kiosk_id"] != kiosk_id:
            raise ValueError(
                f"Token kiosk_id mismatch: token registered to {stored_token['kiosk_id']}, submitted by {kiosk_id}"
            )

        if stored_token["state"] == TokenState.SETTLED.value:
            raise ValueError(f"Token {token_id} has already been settled and closed")

        if stored_token["state"] == TokenState.EXPIRED.value:
            raise ValueError(f"Token {token_id} has expired and was revoked/reclaimed")

        kiosk_key = self._get_kiosk_key(kiosk_id)

        # Verify hash chain integrity and device authentication
        curr_hash = hmac.new(kiosk_key, token_id.encode("utf-8"), hashlib.sha256).hexdigest()
        total_committed_t = 0.0

        for expected_seq, record in enumerate(commitments, start=1):
            if record.get("seq") != expected_seq:
                raise ValueError(
                    f"Sequence gap or reordering: expected seq {expected_seq}, found {record.get('seq')}"
                )

            cid = record.get("commitment_id")
            if not cid:
                raise ValueError(f"Commitment missing unique commitment_id at seq {expected_seq}")

            if cid in self.settled_commitment_ids:
                raise ValueError(f"Replay attack detected: commitment {cid} already settled globally")

            # Verify commitment was admitted within the token's validity window
            if float(record.get("timestamp", 0.0)) > float(token["expires_at"]) + 1e-9:
                raise ValueError(
                    f"Commitment {cid} timestamp ({record.get('timestamp')}) exceeds token validity window ({token['expires_at']})"
                )

            payload = {
                "seq": record["seq"],
                "commitment_id": cid,
                "farmer_id": record["farmer_id"],
                "crop": record["crop"],
                "area_ha": record["area_ha"],
                "required_capacity_t": record["required_capacity_t"],
                "timestamp": record["timestamp"],
            }
            curr_hash = _compute_entry_mac(kiosk_key, curr_hash, payload)
            if not hmac.compare_digest(curr_hash, record.get("hash", "")):
                raise ValueError(
                    f"Hash chain broken at seq {record['seq']}: expected {record.get('hash')}, computed {curr_hash}"
                )
            total_committed_t += float(record["required_capacity_t"])

        if commitments and not hmac.compare_digest(curr_hash, claimed_final_hash or ""):
            raise ValueError("Final hash does not match hash-chain computation")

        allocated_t = float(token["allocated_capacity_t"])
        if total_committed_t > allocated_t + 1e-9:
            raise ValueError(
                f"Total offline commitments ({total_committed_t:.2f}t) exceeded allocated escrow ({allocated_t:.2f}t)"
            )

        # Mark token settled
        stored_token["state"] = TokenState.SETTLED.value
        unused_t = max(0.0, allocated_t - total_committed_t)

        for c in commitments:
            self.settled_commitment_ids.add(c["commitment_id"])
            self.settled_commitments.append(c)

        # Update kiosk stats
        stats = self.kiosk_stats.setdefault(kiosk_id, {"settled_t": 0.0, "sessions": 0})
        stats["settled_t"] += total_committed_t
        stats["sessions"] += 1

        response = {
            "status": "settled",
            "token_id": token_id,
            "kiosk_id": kiosk_id,
            "commitments_accepted": len(commitments),
            "total_committed_t": total_committed_t,
            "reclaimed_unused_capacity_t": unused_t,
            "token_state": TokenState.SETTLED.value,
        }
        self.settlement_cache[token_id] = response
        return response
