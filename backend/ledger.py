import os
import time
import json
import logging
from typing import Dict, Any, Optional

import pandas as pd

from modules.m6_market.supply_ledger import DistrictSupplyLedger

logger = logging.getLogger(__name__)

class LedgerPersistenceManager:
    """
    Handles append-only event logging for the SupplyLedger and 
    materializes the view into memory on boot.
    """
    def __init__(self, data_dir: str = "data/processed", event_file: str = "ledger_events.jsonl"):
        self.data_dir = data_dir
        self.event_file = os.path.join(data_dir, event_file)
        os.makedirs(data_dir, exist_ok=True)
        
    def _append_event(self, event_type: str, district_id: str, payload: Dict[str, Any]):
        """Append an event to the log file."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "district_id": district_id,
            "payload": payload
        }
        with open(self.event_file, 'a') as f:
            f.write(json.dumps(event) + "\n")

    def log_commit(self, district_id: str, farmer_id: str, crop: str, area: float, version: int):
        self._append_event("COMMIT", district_id, {
            "farmer_id": farmer_id,
            "crop": crop,
            "area": area,
            "version": version
        })

    def log_release(self, district_id: str, farmer_id: str, version: int):
        self._append_event("RELEASE", district_id, {
            "farmer_id": farmer_id,
            "version": version
        })

    def hydrate_ledger(self, ledger: DistrictSupplyLedger) -> DistrictSupplyLedger:
        """
        Reconstructs the ledger state by replaying events from the log.
        Matches exact event ordering.
        """
        if not os.path.exists(self.event_file):
            return ledger
            
        with open(self.event_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    # Only replay for the target district
                    if event.get("district_id") != ledger.district_id:
                        continue
                        
                    event_type = event.get("event_type")
                    payload = event.get("payload", {})
                    
                    if event_type == "COMMIT":
                        # Bypass the lock and directly mutate for fast hydration, 
                        # but wait, we can just call commit()
                        # We must catch capacity exceeded to not crash boot, or let it crash if corrupt
                        ledger.commit(
                            payload["farmer_id"], 
                            payload["crop"], 
                            payload["area"]
                        )
                        # Overwrite version to match log
                        ledger.version = payload.get("version", ledger.version)
                        
                    elif event_type == "RELEASE":
                        ledger.release(payload["farmer_id"])
                        ledger.version = payload.get("version", ledger.version)
                        
                except Exception as e:
                    logger.error(f"Failed to replay event {line}: {e}")
                    
        return ledger
