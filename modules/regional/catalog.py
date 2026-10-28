"""Load immutable repaired historical artifacts and bounded classroom scenarios."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import pandas as pd
import yaml

from .economics import finite_number, scenario_row

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO_ID = 'coimbatore-kharif-2019'


class CatalogUnavailableError(RuntimeError):
    """Raised instead of silently serving unrepaired legacy recommendation files."""


class Catalog:
    def __init__(self, active_path: Path | str | None = None):
        self.active_path = Path(active_path or os.environ.get('AGRIINTEL_ACTIVE_RUN', ROOT / 'data/runs/active.json'))
        try:
            pointer = json.loads(self.active_path.read_text())
            run_dir = Path(pointer.get('run_dir', pointer.get('run_id', '')))
            if not run_dir.is_absolute():
                # Active pointer convention: run_dir relative to project, or run_id beside pointer.
                run_dir = ROOT / run_dir if run_dir.as_posix().startswith('data/') else self.active_path.parent / run_dir
            forecast_path = run_dir / pointer.get('forecast_file', 'historical_forecasts.parquet')
            manifest_path = run_dir / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            if manifest.get('status') != 'complete':
                raise ValueError('Active artifact is incomplete')
            manifest_hash = pointer.get('manifest_sha256')
            if manifest_hash and hashlib.sha256(manifest_path.read_bytes()).hexdigest() != manifest_hash:
                raise ValueError('Active manifest hash mismatch')
            forecast_hash = hashlib.sha256(forecast_path.read_bytes()).hexdigest()
            recorded_hash = manifest.get('artifact_sha256', {}).get(pointer.get('forecast_file', 'historical_forecasts.parquet'))
            if not recorded_hash or recorded_hash != forecast_hash:
                raise ValueError('Historical forecast hash mismatch or absent provenance')
            self.frame = pd.read_parquet(forecast_path)
            self.metadata = {
                'artifact_id': pointer['run_id'], 'data_year': int(self.frame['Year_start'].max()),
                'currency_basis': '2011-base INR', 'mode': 'historical_simulation',
                'source_sha256': forecast_hash,
                'price_provenance': 'Generated historical price proxy; not official MSP or observed sale price',
                'cost_provenance': 'Past-only modeled cultivation-cost proxy; not observed farm expenditure',
                'feature_cutoff': 'Prior data years; original publication vintages unverified',
            }
        except (OSError, ValueError, KeyError, ImportError) as exc:
            raise CatalogUnavailableError(f'No validated historical artifact available: {exc}') from exc
        required = {'State', 'District', 'Crop', 'Season', 'Year_start', 'q10', 'q50', 'q90',
                    'Price_Reference_per_Quintal', 'Cost_Proxy_per_Hectare'}
        missing = required.difference(self.frame.columns)
        if missing:
            raise CatalogUnavailableError(f'Artifact is missing columns: {sorted(missing)}')
        latest = self.frame[self.frame.Year_start == self.metadata['data_year']].copy()
        if 'Supported' in latest:
            latest = latest[latest['Supported'].fillna(False).astype(bool)]
        valid = latest[list(required.difference({'State', 'District', 'Crop', 'Season'}))].apply(pd.to_numeric, errors='coerce')
        mask = valid.notna().all(axis=1) & valid.apply(lambda s: s.map(math.isfinite)).all(axis=1)
        mask &= (latest.q10 >= 0) & (latest.q50 >= latest.q10) & (latest.q90 >= latest.q50)
        mask &= (latest.q90 > 0) & (latest.Price_Reference_per_Quintal > 0) & (latest.Cost_Proxy_per_Hectare >= 0)
        self.latest = latest.loc[mask].copy()
        keys = ['State', 'District', 'Crop', 'Season', 'Year_start']
        if self.latest.duplicated(keys).any():
            raise CatalogUnavailableError('Duplicate location/crop/season/year keys in active forecast artifact')
        self.locations: dict = {}
        for (state, district), group in self.latest.groupby(['State', 'District'], observed=True):
            self.locations.setdefault(str(state), {})[str(district)] = sorted(map(str, group.Season.unique()))
        config_path = ROOT / 'config/price_flexibility.yaml'
        self.price_config = yaml.safe_load(config_path.read_text())
        self._scenarios = self._build_scenarios()

    @staticmethod
    def _spec(row: pd.Series) -> dict:
        return {'crop': str(row.Crop), 'yield_q10': float(row.q10), 'yield_q50': float(row.q50),
                'yield_q90': float(row.q90), 'reference_price': float(row.Price_Reference_per_Quintal),
                'cost_per_ha': float(row.Cost_Proxy_per_Hectare)}

    def historical_rows(self, state: str, district: str, season: str, area: float) -> list[dict]:
        area = finite_number(area, 'area', positive=True)
        selected = self.latest[(self.latest.State == state) & (self.latest.District == district) & (self.latest.Season == season)]
        result = []
        for _, row in selected.iterrows():
            spec = self._spec(row)
            reference = spec['reference_price']
            # Explicit +/-10% price stress, not an estimated price distribution.
            result.append(scenario_row(spec, area, reference, reference * .9, reference * 1.1))
        return sorted(result, key=lambda row: (-row['Score'], row['Crop']))

    def _build_scenarios(self) -> list[dict]:
        scenario_path = ROOT / 'config/regional_scenario.yaml'
        cfg = yaml.safe_load(scenario_path.read_text())
        selected = self.latest[(self.latest.State == cfg['state']) & (self.latest.District == cfg['district']) &
                               (self.latest.Season == cfg['season']) & (self.latest.Year_start == cfg['year'])]
        crops = []
        for crop in cfg['crops']:
            match = selected[selected.Crop == crop]
            if len(match) != 1:
                # The configured demo must be unavailable rather than acquire invented yields.
                return []
            spec = self._spec(match.iloc[0])
            coefficients = self.price_config.get('crops', {}).get(crop, {})
            phi = float(coefficients.get('phi', self.price_config['default_flexibility']))
            theta = float(coefficients.get('theta', self.price_config['default_integration']))
            if phi >= 0 or not 0 < theta <= 1 or spec['yield_q50'] <= 0:
                raise CatalogUnavailableError(f'Invalid supply-price scenario configuration for {crop}')
            reference_supply = cfg['reference_area_per_crop_ha'] * spec['yield_q50']
            spec.update(phi=phi, theta=theta, reference_supply_t=reference_supply,
                        outside_supply_t=cfg['outside_share'] * reference_supply,
                        capacity_t=reference_supply * (1 + (cfg['minimum_price_ratio'] - 1) / (phi * theta)))
            crops.append(spec)
        scenario = dict(cfg)
        scenario['template_id'] = cfg['id']
        scenario.update(artifact_id=self.metadata['artifact_id'], crops=crops,
                        currency_basis='2011-base INR', mode='historical_simulation',
                        assumptions='Synthetic reference areas and outside supply; generated price/cost proxies; not observed market supply',
                        price_provenance=self.metadata['price_provenance'], cost_provenance=self.metadata['cost_provenance'])
        # Pin every effective input, not only forecasts. A new run or supply/price
        # configuration gets isolated state without overwriting old commitments.
        fingerprint = hashlib.sha256(json.dumps(scenario, sort_keys=True, allow_nan=False).encode()).hexdigest()[:12]
        scenario['id'] = f"{cfg['id']}--{fingerprint}"
        return [scenario]

    def scenarios(self) -> list[dict]:
        # JSON round trip prevents callers from altering shared artifact configuration.
        return json.loads(json.dumps(self._scenarios))

    def scenario(self, scenario_id: str) -> dict:
        for scenario in self.scenarios():
            if scenario['id'] == scenario_id:
                return scenario
        raise KeyError(f'Unsupported scenario: {scenario_id}')
