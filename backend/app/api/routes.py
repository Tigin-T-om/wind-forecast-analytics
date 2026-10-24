"""FastAPI routes for Wind Forecast Analytics."""

from datetime import datetime, timezone
import logging
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_CUTOFF_POLICY,
    DEFAULT_END_DATE,
    DEFAULT_RESOLUTION,
    DEFAULT_START_DATE,
    SUPPORTED_CUTOFF_POLICIES,
    SUPPORTED_RESOLUTIONS,
)
from backend.app.schemas.responses import (
    AnalysisResponse,
    ForecastSelectionPolicy,
    HealthResponse,
    Observation,
    RequestedPeriod,
    RetrievalStatus,
    SummaryMetrics,
)
from backend.app.services.data_processing import (
    build_observations,
    get_policy_metadata,
    get_resolution_metadata,
    process_actuals,
    process_forecasts,
)
from backend.app.services.elexon_client import ElexonAPIError, ElexonClient
from backend.app.services.metrics import calculate_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])
elexon_client = ElexonClient()

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_dates(start_date: str, end_date: str) -> None:
    """Validate date format and range ordering."""
    if not DATE_REGEX.match(start_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid start_date format '{start_date}'. Expected YYYY-MM-DD.",
        )
    if not DATE_REGEX.match(end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid end_date format '{end_date}'. Expected YYYY-MM-DD.",
        )

    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid calendar date provided: {e}",
        )

    if dt_start > dt_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_date ({start_date}) cannot be later than end_date ({end_date}).",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Probe",
    description="Returns application health status and upstream Elexon BMRS connectivity.",
)
async def health_check() -> HealthResponse:
    """Perform health and upstream connectivity check."""
    upstream_ok = await elexon_client.check_health()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return HealthResponse(
        status="ok",
        app=APP_NAME,
        version=APP_VERSION,
        timestamp=now_utc,
        elexon_upstream="operational" if upstream_ok else "unreachable",
    )


@router.get(
    "/analysis",
    response_model=AnalysisResponse,
    summary="Wind Generation and Forecast Analysis",
    description="Evaluates national UK wind generation forecasts against metered actuals for a date range.",
)
async def get_analysis(
    start_date: str = Query(
        default=DEFAULT_START_DATE,
        description="Analysis start date (YYYY-MM-DD). Defaults to 2026-01-01.",
    ),
    end_date: str = Query(
        default=DEFAULT_END_DATE,
        description="Analysis end date (YYYY-MM-DD). Defaults to 2026-01-31.",
    ),
    cutoff_policy: str = Query(
        default=DEFAULT_CUTOFF_POLICY,
        description="Forecast cutoff selection policy: day_ahead_1700, day_ahead_1200, gate_closure_1h, or latest_prior.",
    ),
    resolution: str = Query(
        default=DEFAULT_RESOLUTION,
        description="Comparison resolution: 'hourly' (energy-weighted average), 'half_hourly' (settlement periods), or 'exact'.",
    ),
) -> AnalysisResponse:
    """Fetch official Elexon FUELHH and WINDFOR streams, apply cutoff policy, and calculate accuracy metrics."""
    # 1. Validation
    validate_dates(start_date, end_date)

    if cutoff_policy not in SUPPORTED_CUTOFF_POLICIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported cutoff_policy '{cutoff_policy}'. "
                f"Must be one of: {sorted(list(SUPPORTED_CUTOFF_POLICIES))}"
            ),
        )

    if resolution not in SUPPORTED_RESOLUTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported resolution '{resolution}'. "
                f"Must be one of: {sorted(list(SUPPORTED_RESOLUTIONS))}"
            ),
        )

    # 2. Upstream Data Fetching
    try:
        raw_actuals, actuals_cached = await elexon_client.fetch_actual_generation(start_date, end_date)
        raw_forecasts, forecasts_cached = await elexon_client.fetch_forecast_generation(start_date, end_date)
    except ElexonAPIError as e:
        logger.error(f"Elexon upstream error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception("Unexpected error communicating with upstream Elexon API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal processing error while communicating with data provider.",
        )

    # 3. Processing and Filtering
    actuals_map = process_actuals(raw_actuals)
    forecasts_map = process_forecasts(raw_forecasts, policy=cutoff_policy)

    obs_dicts, matched_pairs, total_actuals_used, total_expected = build_observations(
        actuals_map=actuals_map,
        forecasts_map=forecasts_map,
        start_date=start_date,
        end_date=end_date,
        resolution=resolution,
    )

    # 4. Metrics Calculation
    missing_actuals_count = sum(1 for o in obs_dicts if o["status"] == "missing_actual")
    missing_forecasts_count = sum(1 for o in obs_dicts if o["status"] == "missing_forecast")

    metrics_res = calculate_metrics(
        pairs=matched_pairs,
        total_expected_intervals=total_expected,
    )

    res_meta = get_resolution_metadata(resolution)

    summary_metrics = SummaryMetrics(
        mae=metrics_res["mae"],
        rmse=metrics_res["rmse"],
        bias=metrics_res["bias"],
        unit=metrics_res["unit"],
        matched_count=metrics_res["matched_count"],
        total_expected_intervals=total_expected,
        total_actual_records=len(actuals_map),
        total_actual_records_used=total_actuals_used,
        total_forecast_records=len(forecasts_map),
        missing_actual_count=missing_actuals_count,
        missing_forecast_count=missing_forecasts_count,
        coverage_percentage=metrics_res["coverage_percentage"],
        resolution=resolution,
        resolution_description=res_meta["description"],
    )

    policy_meta = get_policy_metadata(cutoff_policy)
    forecast_policy = ForecastSelectionPolicy(
        policy_id=policy_meta["policy_id"],
        name=policy_meta["name"],
        description=policy_meta["description"],
        cutoff_rule=policy_meta["cutoff_rule"],
    )

    retrieval_status = RetrievalStatus(
        source="Elexon BMRS (FUELHH actuals & WINDFOR forecasts)",
        cached=(actuals_cached and forecasts_cached),
        fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        warnings=[],
    )

    if summary_metrics.matched_count == 0:
        retrieval_status.warnings.append(
            "No matched intervals found where both actual and forecast observations were available under the selected cutoff policy."
        )

    observations = [Observation(**obs) for obs in obs_dicts]

    return AnalysisResponse(
        requested_period=RequestedPeriod(start_date=start_date, end_date=end_date),
        timezone_convention="UTC",
        forecast_selection_policy=forecast_policy,
        summary_metrics=summary_metrics,
        observations=observations,
        retrieval_status=retrieval_status,
    )
