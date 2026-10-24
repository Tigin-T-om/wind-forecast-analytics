"""Unit tests for data processing, cutoff policies, and interval matching."""

from datetime import datetime, timezone
import pytest

from backend.app.services.data_processing import (
    build_observations,
    format_utc_timestamp,
    get_cutoff_datetime,
    get_resolution_metadata,
    parse_utc_timestamp,
    process_actuals,
    process_forecasts,
)


def test_parse_utc_timestamp():
    """Verify ISO 8601 parsing into UTC datetime."""
    dt1 = parse_utc_timestamp("2026-01-01T12:30:00Z")
    assert dt1 == datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)

    dt2 = parse_utc_timestamp("2026-01-01T12:30:00+00:00")
    assert dt2 == datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)

    assert parse_utc_timestamp(None) is None
    assert parse_utc_timestamp("") is None
    assert parse_utc_timestamp("not-a-timestamp") is None


def test_format_utc_timestamp():
    """Verify datetime formatting into ISO 8601 UTC string."""
    dt = datetime(2026, 1, 15, 8, 45, 0, tzinfo=timezone.utc)
    assert format_utc_timestamp(dt) == "2026-01-15T08:45:00Z"
    assert format_utc_timestamp(None) is None


def test_get_cutoff_datetime_policies():
    """Verify cutoff threshold calculation for various policies."""
    delivery_dt = datetime(2026, 1, 2, 14, 0, 0, tzinfo=timezone.utc)

    cutoff_da17 = get_cutoff_datetime(delivery_dt, "day_ahead_1700")
    assert cutoff_da17 == datetime(2026, 1, 1, 17, 0, 0, tzinfo=timezone.utc)

    cutoff_da12 = get_cutoff_datetime(delivery_dt, "day_ahead_1200")
    assert cutoff_da12 == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    cutoff_gc1h = get_cutoff_datetime(delivery_dt, "gate_closure_1h")
    assert cutoff_gc1h == datetime(2026, 1, 2, 13, 0, 0, tzinfo=timezone.utc)

    cutoff_lp = get_cutoff_datetime(delivery_dt, "latest_prior")
    assert cutoff_lp == datetime(2026, 1, 2, 14, 0, 0, tzinfo=timezone.utc)


def test_process_actuals_filters_wind_and_deduplicates():
    """Verify process_actuals filters fuelType WIND and handles duplicates deterministically."""
    raw_data = [
        {"fuelType": "BIOMASS", "startTime": "2026-01-01T00:00:00Z", "generation": 500},
        {"fuelType": "SOLAR", "startTime": "2026-01-01T00:00:00Z", "generation": 0},
        {
            "fuelType": "WIND",
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2026-01-01T00:30:00Z",
            "generation": 12500,
        },
        {
            "fuelType": "WIND",
            "startTime": "2026-01-01T00:00:00Z",
            "publishTime": "2026-01-01T01:00:00Z",
            "generation": 12600,
        },
        {
            "fuelType": "WIND",
            "startTime": "2026-01-01T00:30:00Z",
            "publishTime": "2026-01-01T01:00:00Z",
            "generation": 12700,
        },
    ]

    actuals_map = process_actuals(raw_data)
    assert len(actuals_map) == 2
    assert "2026-01-01T00:00:00Z" in actuals_map
    assert "2026-01-01T00:30:00Z" in actuals_map
    assert actuals_map["2026-01-01T00:00:00Z"]["generation"] == 12600.0


def test_process_forecasts_cutoff_enforcement():
    """Verify that no forecast published AFTER the cutoff is ever selected."""
    delivery = "2026-01-02T12:00:00Z"

    raw_forecasts = [
        {"startTime": delivery, "publishTime": "2025-12-31T12:00:00Z", "generation": 14000},
        {"startTime": delivery, "publishTime": "2026-01-01T11:30:00Z", "generation": 14500},
        {"startTime": delivery, "publishTime": "2026-01-01T16:30:00Z", "generation": 14800},
        {"startTime": delivery, "publishTime": "2026-01-01T18:30:00Z", "generation": 15500},
        {"startTime": delivery, "publishTime": "2026-01-02T08:00:00Z", "generation": 16000},
    ]

    selected = process_forecasts(raw_forecasts, policy="day_ahead_1700")
    assert delivery in selected
    assert selected[delivery]["generation"] == 14800.0
    assert selected[delivery]["publish_time"] == "2026-01-01T16:30:00Z"

    selected_12 = process_forecasts(raw_forecasts, policy="day_ahead_1200")
    assert selected_12[delivery]["generation"] == 14500.0
    assert selected_12[delivery]["publish_time"] == "2026-01-01T11:30:00Z"


def test_process_forecasts_tie_breaking():
    """Verify deterministic tie-breaking if multiple forecasts share the identical latest publishTime."""
    delivery = "2026-01-02T12:00:00Z"
    same_pub = "2026-01-01T15:00:00Z"

    raw_forecasts = [
        {"startTime": delivery, "publishTime": same_pub, "generation": 10000, "dataset": "WINDFOR"},
        {"startTime": delivery, "publishTime": same_pub, "generation": 12000, "dataset": "WINDFOR"},
    ]

    selected = process_forecasts(raw_forecasts, policy="day_ahead_1700")
    assert selected[delivery]["generation"] == 12000.0


def test_build_observations_hourly_energy_weighted_average():
    """Verify hourly resolution averages both half-hours into true hourly actual generation."""
    actuals_map = {
        "2026-01-01T00:00:00Z": {"generation": 1000.0},
        "2026-01-01T00:30:00Z": {"generation": 1200.0},
    }
    forecasts_map = {
        "2026-01-01T00:00:00Z": {"generation": 1150.0, "publish_time": "2025-12-31T15:00:00Z"},
    }

    obs, pairs, used, total = build_observations(
        actuals_map,
        forecasts_map,
        start_date="2026-01-01",
        end_date="2026-01-01",
        resolution="hourly",
    )

    # 1 day = 24 hours
    assert total == 24
    # Hour 00:00
    h0 = obs[0]
    assert h0["delivery_timestamp"] == "2026-01-01T00:00:00Z"
    # Average of 1000.0 and 1200.0 is 1100.0 MW
    assert h0["actual_mw"] == 1100.0
    assert h0["forecast_mw"] == 1150.0
    assert h0["signed_error"] == 50.0  # 1150 - 1100
    assert h0["status"] == "matched"
    assert used == 2
    assert pairs[0] == (1150.0, 1100.0)


def test_build_observations_half_hourly_block_mapping():
    """Verify half-hourly resolution applies the hourly block forecast to both settlement periods."""
    actuals_map = {
        "2026-01-01T00:00:00Z": {"generation": 1000.0},
        "2026-01-01T00:30:00Z": {"generation": 1200.0},
    }
    forecasts_map = {
        "2026-01-01T00:00:00Z": {"generation": 1100.0, "publish_time": "2025-12-31T15:00:00Z"},
    }

    obs, pairs, used, total = build_observations(
        actuals_map,
        forecasts_map,
        start_date="2026-01-01",
        end_date="2026-01-01",
        resolution="half_hourly",
    )

    # 1 day = 48 half-hours
    assert total == 48
    # SP1: 00:00
    assert obs[0]["delivery_timestamp"] == "2026-01-01T00:00:00Z"
    assert obs[0]["actual_mw"] == 1000.0
    assert obs[0]["forecast_mw"] == 1100.0
    assert obs[0]["signed_error"] == 100.0

    # SP2: 00:30
    assert obs[1]["delivery_timestamp"] == "2026-01-01T00:30:00Z"
    assert obs[1]["actual_mw"] == 1200.0
    assert obs[1]["forecast_mw"] == 1100.0  # Shared block forecast
    assert obs[1]["signed_error"] == -100.0


def test_build_observations_exact_resolution():
    """Verify exact resolution matches on :00 only and leaves :30 as unforecasted."""
    actuals_map = {
        "2026-01-01T00:00:00Z": {"generation": 1000.0},
        "2026-01-01T00:30:00Z": {"generation": 1200.0},
    }
    forecasts_map = {
        "2026-01-01T00:00:00Z": {"generation": 1100.0, "publish_time": "2025-12-31T15:00:00Z"},
    }

    obs, pairs, used, total = build_observations(
        actuals_map,
        forecasts_map,
        start_date="2026-01-01",
        end_date="2026-01-01",
        resolution="exact",
    )

    assert total == 2
    assert obs[0]["status"] == "matched"
    assert obs[1]["status"] == "missing_forecast"
    assert obs[1]["forecast_mw"] is None


def test_get_policy_metadata_all_policies():
    """Verify that get_policy_metadata returns accurate metadata and defaults to day_ahead_1200."""
    from backend.app.services.data_processing import get_policy_metadata

    meta_da12 = get_policy_metadata("day_ahead_1200")
    assert meta_da12["policy_id"] == "day_ahead_1200"
    assert "Auction Cutoff" in meta_da12["name"]
    assert "12:00:00 UTC" in meta_da12["cutoff_rule"]

    meta_da17 = get_policy_metadata("day_ahead_1700")
    assert meta_da17["policy_id"] == "day_ahead_1700"
    assert "Gate Closure" in meta_da17["name"]
    assert "17:00:00 UTC" in meta_da17["cutoff_rule"]

    meta_default = get_policy_metadata("unknown_policy")
    assert meta_default["policy_id"] == "day_ahead_1200"


def test_build_observations_fractional_precision_and_subtraction_exactness():
    """Verify that hourly resolution averages odd half-hour pairs into .5 MW without truncation or drift."""
    actuals_map = {
        # 14,001 + 15,000 = 29,001 -> average = 14,500.5 MW
        "2026-01-01T00:00:00Z": {"generation": 14001, "settlement_period": 1},
        "2026-01-01T00:30:00Z": {"generation": 15000, "settlement_period": 2},
    }
    forecasts_map = {
        "2026-01-01T00:00:00Z": {
            "generation": 16000,
            "publish_time": "2025-12-31T11:00:00Z",
        }
    }

    obs, pairs, used, total = build_observations(
        actuals_map,
        forecasts_map,
        start_date="2026-01-01",
        end_date="2026-01-01",
        resolution="hourly",
    )

    h0 = obs[0]
    assert h0["forecast_mw"] == 16000.0
    assert h0["actual_mw"] == 14500.5
    assert h0["signed_error"] == 1499.5
    assert h0["absolute_error"] == 1499.5
    assert h0["signed_error"] == round(h0["forecast_mw"] - h0["actual_mw"], 2)
    assert h0["absolute_error"] == round(abs(h0["signed_error"]), 2)
