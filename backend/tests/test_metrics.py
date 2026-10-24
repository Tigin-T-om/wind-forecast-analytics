"""Unit tests for accuracy metrics calculation."""

import math
import pytest
from backend.app.services.metrics import calculate_metrics


def test_calculate_metrics_known_values():
    """Verify metrics calculation against a known mathematical example.

    Observations:
        1. Forecast = 100, Actual = 80  -> Error = +20, |Error| = 20, Error^2 = 400
        2. Forecast = 120, Actual = 130 -> Error = -10, |Error| = 10, Error^2 = 100
        3. Forecast = 90,  Actual = 90  -> Error =   0, |Error| =  0, Error^2 =   0

    Expected:
        MAE  = (20 + 10 + 0) / 3 = 10.0
        MSE  = (400 + 100 + 0) / 3 = 166.6667 -> RMSE = sqrt(166.6667) = 12.91
        Bias = (+20 - 10 + 0) / 3 = 3.33 (overforecast bias)
    """
    pairs = [(100.0, 80.0), (120.0, 130.0), (90.0, 90.0)]
    result = calculate_metrics(pairs, total_expected_intervals=3)

    assert result["matched_count"] == 3
    assert result["mae"] == 10.0
    assert result["rmse"] == 12.91
    assert result["bias"] == 3.33
    assert result["unit"] == "MW"
    assert result["coverage_percentage"] == 100.0


def test_calculate_metrics_perfect_forecast():
    """Zero error should produce 0.0 for MAE, RMSE, and Bias."""
    pairs = [(500.0, 500.0), (1250.5, 1250.5)]
    result = calculate_metrics(pairs)

    assert result["matched_count"] == 2
    assert result["mae"] == 0.0
    assert result["rmse"] == 0.0
    assert result["bias"] == 0.0


def test_calculate_metrics_systematic_underforecast():
    """Consistent underforecast should produce a negative bias."""
    pairs = [(100.0, 150.0), (200.0, 250.0)]
    result = calculate_metrics(pairs)

    assert result["matched_count"] == 2
    assert result["mae"] == 50.0
    assert result["rmse"] == 50.0
    assert result["bias"] == -50.0  # Underforecast


def test_calculate_metrics_empty_input():
    """Empty input should return None for metrics without division errors."""
    result = calculate_metrics([], total_expected_intervals=10)

    assert result["matched_count"] == 0
    assert result["mae"] is None
    assert result["rmse"] is None
    assert result["bias"] is None
    assert result["coverage_percentage"] == 0.0


def test_calculate_metrics_none_and_nan_values():
    """Missing or invalid float values must be filtered out gracefully."""
    pairs = [
        (None, 100.0),
        (200.0, None),
        (None, None),
        (float("nan"), 150.0),
        (100.0, float("nan")),
        ("invalid", 100.0),
        (300.0, 200.0),  # Valid: Error = +100
    ]
    result = calculate_metrics(pairs, total_expected_intervals=7)

    assert result["matched_count"] == 1
    assert result["mae"] == 100.0
    assert result["rmse"] == 100.0
    assert result["bias"] == 100.0
    assert result["coverage_percentage"] == round((1 / 7) * 100.0, 1)


def test_calculate_metrics_single_observation():
    """Single observation calculation."""
    pairs = [(150.0, 100.0)]
    result = calculate_metrics(pairs)

    assert result["matched_count"] == 1
    assert result["mae"] == 50.0
    assert result["rmse"] == 50.0
    assert result["bias"] == 50.0
