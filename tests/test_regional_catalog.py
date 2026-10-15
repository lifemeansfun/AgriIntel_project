import json
import hashlib

import pandas as pd
import pytest

from modules.regional.catalog import Catalog, CatalogUnavailableError


def make_catalog(tmp_path, rows):
    run = tmp_path / 'fixture'
    run.mkdir()
    pd.DataFrame(rows).to_parquet(run / 'historical_forecasts.parquet', index=False)
    forecast_hash = hashlib.sha256((run / 'historical_forecasts.parquet').read_bytes()).hexdigest()
    (run / 'manifest.json').write_text(json.dumps({'status': 'complete', 'artifact_sha256': {'historical_forecasts.parquet': forecast_hash}}))
    active = tmp_path / 'active.json'
    active.write_text(json.dumps({'run_id': 'fixture', 'forecast_file': 'historical_forecasts.parquet'}))
    return Catalog(active)


def row(crop='Ragi', **extra):
    return dict(State='Tamil Nadu', District='Coimbatore', Crop=crop, Season='Kharif',
                Year_start=2019, q10=1., q50=2., q90=3., Price_Reference_per_Quintal=1000.,
                Cost_Proxy_per_Hectare=5000., Supported=True, **extra)


def test_no_legacy_fallback(tmp_path):
    with pytest.raises(CatalogUnavailableError, match='No validated'):
        Catalog(tmp_path / 'missing.json')


def test_canonical_historical_row_and_state_isolation(tmp_path):
    other = row('Ragi')
    other.update(State='Other state', Price_Reference_per_Quintal=500)
    cat = make_catalog(tmp_path, [row(), other])
    rows = cat.historical_rows('Tamil Nadu', 'Coimbatore', 'Kharif', 2)
    assert len(rows) == 1
    assert rows[0]['Central_Profit'] == 30000
    assert rows[0]['Pessimistic_Profit'] == 8000
    assert rows[0]['Price_central'] == 1000
    assert rows[0]['Remaining_Area_ha'] is None
    assert 'Other state' in cat.locations
    assert cat.metadata['currency_basis'] == '2011-base INR'
    assert cat.scenarios() == []  # Incomplete scenario is unavailable, never fabricated.


def test_missing_value_is_unavailable_not_zero(tmp_path):
    missing = row()
    missing['Cost_Proxy_per_Hectare'] = float('nan')
    cat = make_catalog(tmp_path, [missing])
    assert cat.historical_rows('Tamil Nadu', 'Coimbatore', 'Kharif', 1) == []
    assert cat.locations == {}


def test_complete_scenario_accounts_for_outside_supply(tmp_path):
    cat = make_catalog(tmp_path, [row('Ragi'), row('Maize'), row('Onion')])
    config = cat.scenarios()[0]
    assert config['participating_area_ha'] == 24
    for spec in config['crops']:
        assert spec['reference_supply_t'] == 80
        assert spec['outside_supply_t'] == 64
        assert spec['capacity_t'] > 80
    config['crops'][0]['reference_price'] = 0
    assert cat.scenarios()[0]['crops'][0]['reference_price'] == 1000


def test_duplicate_forecast_keys_rejected(tmp_path):
    with pytest.raises(CatalogUnavailableError, match='Duplicate'):
        make_catalog(tmp_path, [row(), row()])


def test_effective_configuration_gets_a_new_scenario_identifier(tmp_path):
    cat = make_catalog(tmp_path, [row('Ragi'), row('Maize'), row('Onion')])
    original = cat.scenarios()[0]['id']
    # Forecast bytes stay constant, but a different run identity must not collide.
    cat.metadata['artifact_id'] = 'new-pinned-run'
    different_run = cat._build_scenarios()[0]['id']
    assert different_run != original
    cat.price_config['crops']['Ragi']['theta'] = .5
    different_price_rule = cat._build_scenarios()[0]['id']
    assert different_price_rule != different_run


def test_modified_forecast_fails_closed(tmp_path):
    cat = make_catalog(tmp_path, [row()])
    path = tmp_path / 'fixture/historical_forecasts.parquet'
    frame = pd.read_parquet(path)
    frame.loc[0, 'q50'] = 2.5
    frame.to_parquet(path)
    with pytest.raises(CatalogUnavailableError, match='hash mismatch'):
        Catalog(cat.active_path)
