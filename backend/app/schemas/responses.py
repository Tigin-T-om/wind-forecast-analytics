"""Pydantic models for API request validation and response serialization."""

from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status response."""

    status: str = Field(..., description="Application operational status")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Current server time (ISO 8601 UTC)")
    elexon_upstream: str = Field(..., description="Upstream Elexon BMRS connectivity status")


class RequestedPeriod(BaseModel):
    """Validated requested date range."""

    start_date: str = Field(..., description="Analysis start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Analysis end date (YYYY-MM-DD)")


class ForecastSelectionPolicy(BaseModel):
    """Details of the forecast cutoff policy applied."""

    policy_id: str = Field(..., description="Unique identifier of the cutoff policy")
    name: str = Field(..., description="Human-readable policy name")
    description: str = Field(..., description="Explanation of how forecasts are filtered")
    cutoff_rule: str = Field(..., description="Formal cutoff threshold definition")


class SummaryMetrics(BaseModel):
    """Accuracy metrics and observation counts calculated across matched records."""

    mae: Optional[float] = Field(None, description="Mean Absolute Error in MW (None if no matched records)")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error in MW (None if no matched records)")
    bias: Optional[float] = Field(None, description="Mean Signed Error in MW (Forecast - Actual; positive = overforecast)")
    unit: str = Field("MW", description="Generation and error unit of measurement")
    matched_count: int = Field(..., description="Number of intervals with both valid actual and forecast values")
    total_expected_intervals: int = Field(..., description="Total intervals in the requested period at chosen resolution")
    total_actual_records: int = Field(..., description="Total raw actual generation records retrieved for period")
    total_actual_records_used: int = Field(..., description="Total raw actual generation records incorporated into the analysis")
    total_forecast_records: int = Field(..., description="Total forecast generation records retrieved for period")
    missing_actual_count: int = Field(..., description="Intervals where forecast exists but actual is missing")
    missing_forecast_count: int = Field(..., description="Intervals where actual exists but eligible forecast is missing")
    coverage_percentage: Optional[float] = Field(None, description="Percentage of delivery intervals successfully matched")
    resolution: str = Field("hourly", description="Applied comparison resolution ('hourly', 'half_hourly', or 'exact')")
    resolution_description: str = Field(..., description="Explanation of resolution and aggregation methodology")


class Observation(BaseModel):
    """Single delivery interval observation comparing actual and forecast."""

    delivery_timestamp: str = Field(..., description="Start of the delivery interval in UTC (ISO 8601)")
    delivery_end_timestamp: Optional[str] = Field(None, description="End of the delivery interval in UTC (ISO 8601)")
    forecast_publish_time: Optional[str] = Field(None, description="Publication timestamp of the selected forecast in UTC")
    forecast_mw: Optional[float] = Field(None, description="Selected forecast generation value in MW")
    actual_mw: Optional[float] = Field(None, description="Actual metered wind generation value in MW")
    signed_error: Optional[float] = Field(None, description="Signed error = forecast_mw - actual_mw")
    absolute_error: Optional[float] = Field(None, description="Absolute error = |forecast_mw - actual_mw|")
    status: str = Field(..., description="Interval status: 'matched', 'missing_forecast', or 'missing_actual'")


class RetrievalStatus(BaseModel):
    """Provenance and metadata regarding data extraction."""

    source: str = Field("Elexon BMRS (FUELHH & WINDFOR streams)", description="Primary data source")
    cached: bool = Field(False, description="Whether the response was served from cache")
    fetched_at: str = Field(..., description="Timestamp when data was retrieved or processed (UTC)")
    warnings: List[str] = Field(default_factory=list, description="Any data quality notes or upstream warnings")


class AnalysisResponse(BaseModel):
    """Complete analysis response payload."""

    requested_period: RequestedPeriod
    timezone_convention: str = Field("UTC", description="All timestamps are expressed in UTC")
    forecast_selection_policy: ForecastSelectionPolicy
    summary_metrics: SummaryMetrics
    observations: List[Observation]
    retrieval_status: RetrievalStatus


class ErrorResponse(BaseModel):
    """Standardized API error response."""

    error: str = Field(..., description="Error category code")
    message: str = Field(..., description="Human-readable error description")
    detail: Optional[str] = Field(None, description="Additional context if appropriate")
