"""Async HTTP client for official Elexon BMRS API streams."""

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx

from backend.app.config import (
    CACHE_TTL_SECONDS,
    FUELHH_STREAM_URL,
    HTTP_TIMEOUT_SECONDS,
    WINDFOR_STREAM_URL,
)

logger = logging.getLogger(__name__)


class ElexonAPIError(Exception):
    """Custom exception raised when upstream Elexon BMRS API fails."""

    def __init__(self, message: str, status_code: int = 502, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ElexonClient:
    """Async client for fetching FUELHH and WINDFOR streams from Elexon BMRS."""

    def __init__(
        self,
        timeout: float = HTTP_TIMEOUT_SECONDS,
        cache_ttl: int = CACHE_TTL_SECONDS,
    ):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            cached_time, data = self._cache[key]
            if (time.time() - cached_time) < self.cache_ttl:
                return data
            else:
                del self._cache[key]
        return None

    def _set_in_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (time.time(), data)

    async def check_health(self) -> bool:
        """Check if Elexon API is responsive."""
        cache_key = "health_check"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    FUELHH_STREAM_URL,
                    params={
                        "publishDateTimeFrom": "2026-01-01T00:00:00Z",
                        "publishDateTimeTo": "2026-01-01T00:30:00Z",
                    },
                    headers={"Accept": "application/json"},
                )
                is_healthy = (r.status_code == 200)
                self._set_in_cache(cache_key, is_healthy)
                return is_healthy
        except Exception as e:
            logger.warning(f"Elexon health probe failed: {e}")
            self._set_in_cache(cache_key, False)
            return False

    async def fetch_actual_generation(
        self,
        start_date: str,
        end_date: str,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch actual generation stream (FUELHH) for the given settlement date range.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD

        Returns:
            Tuple of (records_list, is_from_cache)
        """
        cache_key = f"fuelhh_{start_date}_{end_date}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data, True

        params = {
            "settlementDateFrom": start_date,
            "settlementDateTo": end_date,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    FUELHH_STREAM_URL,
                    params=params,
                    headers={"Accept": "application/json", "User-Agent": "WindForecastAnalytics/1.0"},
                )

            if response.status_code != 200:
                raise ElexonAPIError(
                    message=f"Elexon FUELHH endpoint returned HTTP {response.status_code}",
                    status_code=response.status_code if response.status_code in (400, 404, 503) else 502,
                    detail=response.text[:200],
                )

            data = response.json()
            if not isinstance(data, list):
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                else:
                    data = []

            self._set_in_cache(cache_key, data)
            return data, False

        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching FUELHH from Elexon: {e}")
            raise ElexonAPIError(
                message="Upstream Elexon BMRS API request timed out while fetching actual generation",
                status_code=504,
                detail=str(e),
            )
        except httpx.RequestError as e:
            logger.error(f"Network error fetching FUELHH from Elexon: {e}")
            raise ElexonAPIError(
                message="Unable to connect to upstream Elexon BMRS API",
                status_code=502,
                detail=str(e),
            )

    async def fetch_forecast_generation(
        self,
        start_date: str,
        end_date: str,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch wind forecast stream (WINDFOR) for delivery intervals in start_date..end_date.

        Expands the publication window backwards by 5 days to ensure capturing all forecasts
        published in advance of delivery.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD

        Returns:
            Tuple of (records_list, is_from_cache)
        """
        cache_key = f"windfor_{start_date}_{end_date}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data, True

        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ElexonAPIError("Invalid date format, expected YYYY-MM-DD", status_code=400)

        pub_start = (dt_start - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")
        pub_end = (dt_end + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59Z")

        params = {
            "publishDateTimeFrom": pub_start,
            "publishDateTimeTo": pub_end,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    WINDFOR_STREAM_URL,
                    params=params,
                    headers={"Accept": "application/json", "User-Agent": "WindForecastAnalytics/1.0"},
                )

            if response.status_code != 200:
                raise ElexonAPIError(
                    message=f"Elexon WINDFOR endpoint returned HTTP {response.status_code}",
                    status_code=response.status_code if response.status_code in (400, 404, 503) else 502,
                    detail=response.text[:200],
                )

            data = response.json()
            if not isinstance(data, list):
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                else:
                    data = []

            self._set_in_cache(cache_key, data)
            return data, False

        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching WINDFOR from Elexon: {e}")
            raise ElexonAPIError(
                message="Upstream Elexon BMRS API request timed out while fetching forecast generation",
                status_code=504,
                detail=str(e),
            )
        except httpx.RequestError as e:
            logger.error(f"Network error fetching WINDFOR from Elexon: {e}")
            raise ElexonAPIError(
                message="Unable to connect to upstream Elexon BMRS API",
                status_code=502,
                detail=str(e),
            )
