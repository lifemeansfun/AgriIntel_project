"""Compatibility entry point for immutable, raw-source historical training.

Legacy processed predictions and reports are preserved. New runs use the corrected
pipeline and can be located through data/runs/active.json.
"""
from datetime import datetime, timezone
from modules.regional_data.train import main, train_run


def run_ensemble(run_id: str | None = None):
    run_id = run_id or "regional-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return train_run(run_id)


if __name__ == "__main__":
    main()
