"""API integration and endpoint tests."""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.services.elexon_client import ElexonAPIError

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint response structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data
    assert "timestamp" in data
    assert data["elexon_upstream"] in ("operational", "unreachable")


def test_analysis_endpoint_invalid_date_format():
    """Verify 400 Bad Request on invalid date format."""
    response = client.get("/api/analysis?start_date=2026/01/01&end_date=2026-01-05")
    assert response.status_code == 400
    assert "Invalid start_date format" in response.json()["detail"]


def test_analysis_endpoint_inverted_dates():
    """Verify 400 Bad Request when start_date is after end_date."""
    response = client.get("/api/analysis?start_date=2026-01-10&end_date=2026-01-05")
    assert response.status_code == 400
    assert "cannot be later than" in response.json()["detail"]


def test_analysis_endpoint_unsupported_cutoff_policy():
    """Verify 400 Bad Request on unknown cutoff policy."""
    response = client.get("/api/analysis?cutoff_policy=invalid_policy_name")
    assert response.status_code == 400
    assert "Unsupported cutoff_policy" in response.json()["detail"]


def test_analysis_endpoint_unsupported_resolution():
    """Verify 400 Bad Request on unknown resolution."""
    response = client.get("/api/analysis?resolution=invalid_resolution")
    assert response.status_code == 400
    assert "Unsupported resolution" in response.json()["detail"]


@patch("backend.app.api.routes.elexon_client.fetch_actual_generation")
@patch("backend.app.api.routes.elexon_client.fetch_forecast_generation")
def test_analysis_endpoint_hourly_resolution_success(mock_forecasts, mock_actuals):
    """Verify full analysis workflow with hourly energy-weighted aggregation."""
    # 2 half-hours: 00:00 (14000 MW) and 00:30 (16000 MW) -> Hourly average = 15000 MW
    mock_actuals.return_value = (
        [
            {
                "fuelType": "WIND",
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2026-01-01T00:30:00Z",
                "generation": 14000,
            },
            {
                "fuelType": "WIND",
                "startTime": "2026-01-01T00:30:00Z",
                "publishTime": "2026-01-01T01:00:00Z",
                "generation": 16000,
            },
        ],
        False,
    )

    mock_forecasts.return_value = (
        [
            {
                "dataset": "WINDFOR",
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T15:00:00Z",
                "generation": 15500,
            }
        ],
        False,
    )

    response = client.get(
        "/api/analysis?start_date=2026-01-01&end_date=2026-01-01&cutoff_policy=day_ahead_1700&resolution=hourly"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["timezone_convention"] == "UTC"
    assert data["requested_period"]["start_date"] == "2026-01-01"
    assert data["requested_period"]["end_date"] == "2026-01-01"
    assert data["forecast_selection_policy"]["policy_id"] == "day_ahead_1700"

    metrics = data["summary_metrics"]
    assert metrics["matched_count"] == 1
    assert metrics["total_actual_records_used"] == 2
    # Actual average = 15000 MW, Forecast = 15500 MW -> Error = +500 MW
    assert metrics["mae"] == 500.0
    assert metrics["rmse"] == 500.0
    assert metrics["bias"] == 500.0
    assert metrics["resolution"] == "hourly"

    # Observation check
    obs = data["observations"]
    assert len(obs) == 24  # 24 hours in a day
    h0 = obs[0]
    assert h0["delivery_timestamp"] == "2026-01-01T00:00:00Z"
    assert h0["forecast_mw"] == 15500.0
    assert h0["actual_mw"] == 15000.0
    assert h0["signed_error"] == 500.0
    assert h0["status"] == "matched"


@patch("backend.app.api.routes.elexon_client.fetch_actual_generation")
@patch("backend.app.api.routes.elexon_client.fetch_forecast_generation")
def test_analysis_endpoint_policy_sensitivity(mock_forecasts, mock_actuals):
    """Verify that different cutoff policies select different forecasts based on publication time."""
    mock_actuals.return_value = (
        [
            {"fuelType": "WIND", "startTime": "2026-01-02T12:00:00Z", "generation": 10000},
            {"fuelType": "WIND", "startTime": "2026-01-02T12:30:00Z", "generation": 10000},
        ],
        False,
    )

    # 3 forecasts published at different times
    mock_forecasts.return_value = (
        [
            # Available by 12:00 D-1
            {"dataset": "WINDFOR", "startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T11:00:00Z", "generation": 11000},
            # Available by 17:00 D-1
            {"dataset": "WINDFOR", "startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T16:00:00Z", "generation": 12000},
            # Available by Gate Closure (1h prior)
            {"dataset": "WINDFOR", "startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-02T10:00:00Z", "generation": 13000},
        ],
        False,
    )

    # 1. Day-Ahead 12:00
    res_12 = client.get("/api/analysis?start_date=2026-01-02&end_date=2026-01-02&cutoff_policy=day_ahead_1200")
    assert res_12.json()["summary_metrics"]["bias"] == 1000.0  # 11000 - 10000

    # 2. Day-Ahead 17:00
    res_17 = client.get("/api/analysis?start_date=2026-01-02&end_date=2026-01-02&cutoff_policy=day_ahead_1700")
    assert res_17.json()["summary_metrics"]["bias"] == 2000.0  # 12000 - 10000

    # 3. Gate Closure 1h
    res_gc = client.get("/api/analysis?start_date=2026-01-02&end_date=2026-01-02&cutoff_policy=gate_closure_1h")
    assert res_gc.json()["summary_metrics"]["bias"] == 3000.0  # 13000 - 10000


@patch("backend.app.api.routes.elexon_client.fetch_actual_generation")
def test_analysis_endpoint_upstream_error(mock_actuals):
    """Verify proper error propagation when upstream Elexon API fails."""
    mock_actuals.side_effect = ElexonAPIError(
        message="Upstream Elexon BMRS API request timed out",
        status_code=504,
    )

    response = client.get("/api/analysis")
    assert response.status_code == 504
    data = response.json()
    assert "timed out" in data["detail"]


@patch("backend.app.api.routes.elexon_client.fetch_actual_generation")
@patch("backend.app.api.routes.elexon_client.fetch_forecast_generation")
def test_analysis_endpoint_default_parameters(mock_forecasts, mock_actuals):
    """Verify that calling /api/analysis with no params defaults to day_ahead_1200 and hourly resolution."""
    mock_actuals.return_value = (
        [
            {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 10000},
            {"fuelType": "WIND", "startTime": "2026-01-01T00:30:00Z", "generation": 10000},
        ],
        False,
    )
    mock_forecasts.return_value = (
        [
            {"dataset": "WINDFOR", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T11:00:00Z", "generation": 11000},
        ],
        False,
    )

    response = client.get("/api/analysis")
    assert response.status_code == 200
    data = response.json()

    assert data["forecast_selection_policy"]["policy_id"] == "day_ahead_1200"
    assert "Auction Cutoff" in data["forecast_selection_policy"]["name"]
    assert data["summary_metrics"]["resolution"] == "hourly"
    assert data["requested_period"]["start_date"] == "2026-01-01"
    assert data["requested_period"]["end_date"] == "2026-01-31"


@patch("backend.app.api.routes.elexon_client.fetch_actual_generation")
@patch("backend.app.api.routes.elexon_client.fetch_forecast_generation")
def test_analysis_endpoint_observation_error_integrity(mock_forecasts, mock_actuals):
    """Verify that every matched observation satisfies signed_error = forecast - actual and abs_error = |signed_error|."""
    mock_actuals.return_value = (
        [
            # Odd sum creates .5 MW average: (14001 + 15000) / 2 = 14500.5 MW
            {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 14001},
            {"fuelType": "WIND", "startTime": "2026-01-01T00:30:00Z", "generation": 15000},
            # Even sum: (10000 + 12000) / 2 = 11000.0 MW
            {"fuelType": "WIND", "startTime": "2026-01-01T01:00:00Z", "generation": 10000},
            {"fuelType": "WIND", "startTime": "2026-01-01T01:30:00Z", "generation": 12000},
        ],
        False,
    )
    mock_forecasts.return_value = (
        [
            {"dataset": "WINDFOR", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T11:00:00Z", "generation": 16000},
            {"dataset": "WINDFOR", "startTime": "2026-01-01T01:00:00Z", "publishTime": "2025-12-31T11:00:00Z", "generation": 10500},
        ],
        False,
    )

    response = client.get("/api/analysis?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200
    data = response.json()

    matched_obs = [o for o in data["observations"] if o["status"] == "matched"]
    assert len(matched_obs) == 2

    # Hour 0: 16000 - 14500.5 = +1499.5 MW
    h0 = matched_obs[0]
    assert h0["forecast_mw"] == 16000.0
    assert h0["actual_mw"] == 14500.5
    assert h0["signed_error"] == 1499.5
    assert h0["absolute_error"] == 1499.5
    assert round(h0["forecast_mw"] - h0["actual_mw"], 2) == h0["signed_error"]
    assert round(abs(h0["signed_error"]), 2) == h0["absolute_error"]

    # Hour 1: 10500 - 11000 = -500.0 MW
    h1 = matched_obs[1]
    assert h1["forecast_mw"] == 10500.0
    assert h1["actual_mw"] == 11000.0
    assert h1["signed_error"] == -500.0
    assert h1["absolute_error"] == 500.0
    assert round(h1["forecast_mw"] - h1["actual_mw"], 2) == h1["signed_error"]
    assert round(abs(h1["signed_error"]), 2) == h1["absolute_error"]
