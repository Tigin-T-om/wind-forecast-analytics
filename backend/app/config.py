"""Configuration module for Wind Forecast Analytics application."""

import os
from typing import Set

# Application metadata
APP_NAME: str = "Wind Forecast Analytics"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "UK Electricity Utility Wind Generation vs Forecast Analytics"

# Official Elexon BMRS Endpoints
ELEXON_BASE_URL: str = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
FUELHH_STREAM_URL: str = f"{ELEXON_BASE_URL}/datasets/FUELHH/stream"
WINDFOR_STREAM_URL: str = f"{ELEXON_BASE_URL}/datasets/WINDFOR/stream"

# Default Analysis Window
DEFAULT_START_DATE: str = os.getenv("DEFAULT_START_DATE", "2026-01-01")
DEFAULT_END_DATE: str = os.getenv("DEFAULT_END_DATE", "2026-01-31")

# Supported Forecast Selection Policies
SUPPORTED_CUTOFF_POLICIES: Set[str] = {
    "day_ahead_1700",  # Cutoff at 17:00 UTC day-ahead (D-1)
    "day_ahead_1200",  # Cutoff at 12:00 UTC day-ahead (D-1)
    "gate_closure_1h",  # 1 hour prior to delivery interval start
    "latest_prior",     # Latest forecast published prior to delivery start
}
DEFAULT_CUTOFF_POLICY: str = os.getenv("DEFAULT_CUTOFF_POLICY", "day_ahead_1700")

# Supported Resolution Modes
SUPPORTED_RESOLUTIONS: Set[str] = {
    "hourly",       # Energy-weighted average of 30-min actuals matching hourly forecast (100% coverage)
    "half_hourly",  # 30-min settlement intervals with hourly block forecast applied (100% coverage)
    "exact",        # Exact delivery timestamp match only (:00 matches, :30 unforecasted)
}
DEFAULT_RESOLUTION: str = os.getenv("DEFAULT_RESOLUTION", "hourly")

# HTTP and Cache Settings
HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30.0"))
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# Display and Units
ENERGY_UNIT: str = "MW"
TIMEZONE: str = "UTC"
