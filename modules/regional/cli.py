"""Reproducible artifact checks and classroom replay (no running web server needed)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .catalog import Catalog
from .ledger import RegionalLedger
from .replay import ReplayService


def verify_artifacts(active_path=None):
    catalog = Catalog(active_path)
    pointer = json.loads(catalog.active_path.read_text())
    run = Path(pointer.get('run_dir', pointer['run_id']))
    if not run.is_absolute():
        from .catalog import ROOT
        run = ROOT / run if run.as_posix().startswith('data/') else catalog.active_path.parent / run
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('status') != 'complete':
        raise ValueError('Active run is not complete')
    expected_manifest = pointer.get('manifest_sha256')
    if expected_manifest and hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected_manifest:
        raise ValueError('Active manifest hash mismatch')
    for relative, expected in manifest.get('artifact_sha256', {}).items():
        target = (run / relative).resolve()
        if not target.is_relative_to(run.resolve()):
            raise ValueError('Artifact path leaves the run directory')
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Artifact hash mismatch: {relative}')
    if len(catalog.locations) != 5 or len(catalog.scenarios()) != 1:
        raise ValueError('Expected five historical states and one supported regional demo')
    return {'status': 'pass', **catalog.metadata, 'historical_states': sorted(catalog.locations),
            'supported_latest_rows': len(catalog.latest), 'feedback_scenario': catalog.scenarios()[0]['id'],
            'metrics': json.loads((run / 'metrics.json').read_text())['overall']}


def run_replay(output_dir: Path, seed: int = 42, active_path=None):
    catalog = Catalog(active_path)
    scenario = catalog.scenarios()[0]
    output_dir.mkdir(parents=True, exist_ok=False)
    ledger = RegionalLedger(output_dir / 'replay.sqlite3')
    replay_service = ReplayService(ledger)
    result = replay_service.create(scenario, seed)
    while result['status'] != 'completed':
        result = replay_service.step(result['id'])
    (output_dir / 'replay.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    report = {'artifact_id': catalog.metadata['artifact_id'], 'seed': seed,
              'comparison_note': result['comparison_note'], 'summary': result['summary']}
    (output_dir / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-path', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify-artifacts')
    replay = commands.add_parser('replay')
    replay.add_argument('--seed', type=int, default=42)
    replay.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = verify_artifacts(args.active_path) if args.command == 'verify-artifacts' else run_replay(args.output_dir, args.seed, args.active_path)
    # Keep terminal output compact; detailed participant outcomes are in summary.json.
    if args.command == 'replay':
        result = dict(result, summary={policy: {k: v for k, v in outcome.items() if k != 'participant_profits'}
                                      for policy, outcome in result['summary'].items()})
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
