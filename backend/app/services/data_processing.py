"""Data processing, cutoff policies, and interval matching module.

Handles timestamp normalization, actual wind filtering, deterministic cutoff-based
forecast selection, and defensible comparison between hourly forecasts and half-hourly actuals.
Implemented strictly with Python standard library (no pandas).
"""

from datetime import datetime, time, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import SUPPORTED_CUTOFF_POLICIES, SUPPORTED_RESOLUTIONS


def parse_utc_timestamp(ts: Any) -> Optional[datetime]:
    """Parse various ISO 8601 timestamp formats into a timezone-aware UTC datetime.

    Args:
        ts: Timestamp string or datetime object.

    Returns:
        Timezone-aware datetime in UTC, or None if parsing fails.
    """
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    if not isinstance(ts, str):
        return None

    cleaned = ts.strip()
    if not cleaned:
        return None

    try:
        iso_str = cleaned.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def format_utc_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format a datetime into standard ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SSZ)."""
    if dt is None:
        return None
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_cutoff_datetime(delivery_dt: datetime, policy: str) -> datetime:
    """Calculate the exact cutoff datetime for a delivery interval under a chosen policy.

    Args:
        delivery_dt: UTC delivery interval start time.
        policy: One of the supported cutoff policy identifiers.

    Returns:
        Cutoff datetime in UTC. Forecasts published after this threshold are ineligible.
    """
    delivery_date = delivery_dt.date()
    day_ahead_date = delivery_date - timedelta(days=1)

    if policy == "day_ahead_1700":
        # Day-Ahead Gate: 17:00:00 UTC on D-1
        return datetime.combine(day_ahead_date, time(17, 0, 0), tzinfo=timezone.utc)
    elif policy == "day_ahead_1200":
        # Day-Ahead Auction cutoff: 12:00:00 UTC on D-1
        return datetime.combine(day_ahead_date, time(12, 0, 0), tzinfo=timezone.utc)
    elif policy == "gate_closure_1h":
        # Gate Closure: 1 hour prior to delivery interval start
        return delivery_dt - timedelta(hours=1)
    elif policy == "latest_prior":
        # Intra-day: latest published strictly prior to or at delivery start
        return delivery_dt
    else:
        return datetime.combine(day_ahead_date, time(17, 0, 0), tzinfo=timezone.utc)


def get_policy_metadata(policy: str) -> Dict[str, str]:
    """Return descriptive metadata for a cutoff policy."""
    policies = {
        "day_ahead_1700": {
            "policy_id": "day_ahead_1700",
            "name": "Day-Ahead 17:00 UTC Cutoff",
            "description": "Selects the latest forecast published by 17:00 UTC on the day prior to delivery (D-1).",
            "cutoff_rule": "publishTime <= (DeliveryDate - 1 day) at 17:00:00 UTC",
        },
        "day_ahead_1200": {
            "policy_id": "day_ahead_1200",
            "name": "Day-Ahead 12:00 UTC Cutoff",
            "description": "Selects the latest forecast published by 12:00 UTC on the day prior to delivery (D-1), matching day-ahead power auction timelines.",
            "cutoff_rule": "publishTime <= (DeliveryDate - 1 day) at 12:00:00 UTC",
        },
        "gate_closure_1h": {
            "policy_id": "gate_closure_1h",
            "name": "Gate Closure (1 Hour Prior)",
            "description": "Selects the latest forecast published at least 1 hour before delivery interval commencement.",
            "cutoff_rule": "publishTime <= deliveryStartTime - 1 hour",
        },
        "latest_prior": {
            "policy_id": "latest_prior",
            "name": "Latest Prior to Delivery",
            "description": "Selects the latest forecast published prior to or at the start of delivery.",
            "cutoff_rule": "publishTime <= deliveryStartTime",
        },
    }
    return policies.get(policy, policies["day_ahead_1700"])


def get_resolution_metadata(resolution: str) -> Dict[str, str]:
    """Return descriptive metadata and justification for the comparison resolution."""
    resolutions = {
        "hourly": {
            "resolution": "hourly",
            "name": "Hourly Energy-Weighted Average (100% Coverage)",
            "description": (
                "Aggregates the two 30-minute actual settlement periods in each hour into "
                "the true energy-weighted average power generation. Compares 1-hour forecast against "
                "1-hour actual output without discarding any actual data (100% coverage)."
            ),
        },
        "half_hourly": {
            "resolution": "half_hourly",
            "name": "Half-Hourly Settlement Intervals (100% Coverage)",
            "description": (
                "Maps the Day-Ahead hourly block forecast to both 30-minute settlement periods in each hour, "
                "matching the UK Balancing Mechanism settlement timeline (100% coverage)."
            ),
        },
        "exact": {
            "resolution": "exact",
            "name": "Exact Delivery Timestamp Matching (:00 only)",
            "description": (
                "Strict string matching on delivery timestamp. Matches :00 intervals only; :30 intervals are treated as unforecasted."
            ),
        },
    }
    return resolutions.get(resolution, resolutions["hourly"])


def process_actuals(raw_actuals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Filter raw FUELHH records to WIND and index by delivery timestamp.

    Handles duplicates deterministically by retaining the record with latest publishTime
    or greatest generation value if publishTime is identical.

    Args:
        raw_actuals: List of raw records from FUELHH endpoint.

    Returns:
        Dict mapping ISO delivery timestamp to actual record dict.
    """
    actuals_by_delivery: Dict[str, Dict[str, Any]] = {}

    for item in raw_actuals:
        if item.get("fuelType") != "WIND":
            continue

        raw_start = item.get("startTime")
        start_dt = parse_utc_timestamp(raw_start)
        if not start_dt:
            continue

        iso_key = format_utc_timestamp(start_dt)
        raw_gen = item.get("generation")
        try:
            gen_val = float(raw_gen) if raw_gen is not None else None
        except (ValueError, TypeError):
            continue

        if gen_val is None or math.isnan(gen_val):
            continue

        publish_dt = parse_utc_timestamp(item.get("publishTime"))

        record = {
            "delivery_timestamp": iso_key,
            "delivery_dt": start_dt,
            "publish_dt": publish_dt,
            "publish_time": format_utc_timestamp(publish_dt),
            "generation": round(gen_val, 2),
            "settlement_date": item.get("settlementDate"),
            "settlement_period": item.get("settlementPeriod"),
        }

        # Deterministic deduplication
        if iso_key in actuals_by_delivery:
            existing = actuals_by_delivery[iso_key]
            ex_pub = existing.get("publish_dt")
            cur_pub = record.get("publish_dt")
            if cur_pub and ex_pub:
                if cur_pub > ex_pub:
                    actuals_by_delivery[iso_key] = record
                elif cur_pub == ex_pub and record["generation"] > existing["generation"]:
                    actuals_by_delivery[iso_key] = record
            elif cur_pub and not ex_pub:
                actuals_by_delivery[iso_key] = record
        else:
            actuals_by_delivery[iso_key] = record

    return actuals_by_delivery


def process_forecasts(
    raw_forecasts: List[Dict[str, Any]],
    policy: str = "day_ahead_1700",
) -> Dict[str, Dict[str, Any]]:
    """Group forecasts by delivery timestamp and select the eligible forecast per cutoff policy.

    Selection Rule:
        1. Consider only forecasts where publishTime <= cutoff(delivery_dt, policy).
        2. Never select a forecast published after the cutoff.
        3. Deterministically select the forecast with the latest publishTime.
        4. If ties occur on publishTime, break ties by (generation, dataset).

    Args:
        raw_forecasts: List of raw records from WINDFOR endpoint.
        policy: Chosen cutoff policy.

    Returns:
        Dict mapping ISO delivery timestamp to selected forecast record dict.
    """
    forecasts_by_delivery: Dict[str, List[Dict[str, Any]]] = {}

    for item in raw_forecasts:
        start_dt = parse_utc_timestamp(item.get("startTime"))
        pub_dt = parse_utc_timestamp(item.get("publishTime"))
        if not start_dt or not pub_dt:
            continue

        raw_gen = item.get("generation")
        try:
            gen_val = float(raw_gen) if raw_gen is not None else None
        except (ValueError, TypeError):
            continue

        if gen_val is None or math.isnan(gen_val):
            continue

        iso_key = format_utc_timestamp(start_dt)
        entry = {
            "delivery_timestamp": iso_key,
            "delivery_dt": start_dt,
            "publish_dt": pub_dt,
            "publish_time": format_utc_timestamp(pub_dt),
            "generation": round(gen_val, 2),
            "dataset": str(item.get("dataset", "WINDFOR")),
        }

        if iso_key not in forecasts_by_delivery:
            forecasts_by_delivery[iso_key] = []
        forecasts_by_delivery[iso_key].append(entry)

    selected_forecasts: Dict[str, Dict[str, Any]] = {}

    for iso_key, candidates in forecasts_by_delivery.items():
        if not candidates:
            continue
        delivery_dt = candidates[0]["delivery_dt"]
        cutoff_dt = get_cutoff_datetime(delivery_dt, policy)

        # Filter strictly to forecasts published on or before cutoff
        eligible = [c for c in candidates if c["publish_dt"] <= cutoff_dt]
        if not eligible:
            continue

        # Sort key: publish_dt ascending, generation ascending, dataset ascending
        eligible.sort(key=lambda x: (x["publish_dt"], x["generation"], x["dataset"]))
        best = eligible[-1]
        selected_forecasts[iso_key] = best

    return selected_forecasts


def build_observations(
    actuals_map: Dict[str, Dict[str, Any]],
    forecasts_map: Dict[str, Dict[str, Any]],
    start_date: str,
    end_date: str,
    resolution: str = "hourly",
) -> Tuple[List[Dict[str, Any]], List[Tuple[Optional[float], Optional[float]]], int, int]:
    """Merge actuals and forecasts into chronologically sorted observations.

    Handles resolution differences rigorously:
    - "hourly": Energy-weighted average of both 30-min actuals in each hour.
      Compares true 1-hour generation against 1-hour forecast (100% data coverage).
    - "half_hourly": Maps the Day-Ahead 1-hour block forecast to each 30-minute settlement period.
    - "exact": Strict match on :00 intervals only (legacy 50% coverage).

    Args:
        actuals_map: Map of delivery timestamp to actual generation.
        forecasts_map: Map of delivery timestamp to selected forecast generation.
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        resolution: "hourly", "half_hourly", or "exact"

    Returns:
        Tuple of:
          - observations: Chronologically sorted list of observation dicts.
          - matched_pairs: List of (forecast_mw, actual_mw) for metrics computation.
          - total_actuals_used: Count of raw half-hour actuals incorporated.
          - total_expected_intervals: Count of expected timeline intervals.
    """
    dt_cur = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt_end = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).replace(tzinfo=timezone.utc)

    observations: List[Dict[str, Any]] = []
    matched_pairs: List[Tuple[Optional[float], Optional[float]]] = []
    total_actuals_used = 0

    if resolution == "hourly":
        # Hourly Resolution: Step through hour by hour
        while dt_cur < dt_end:
            ts_start = format_utc_timestamp(dt_cur)
            dt_next = dt_cur + timedelta(hours=1)
            ts_end = format_utc_timestamp(dt_next)

            # Retrieve both half-hour settlement periods in this hour
            dt_30 = dt_cur + timedelta(minutes=30)
            ts_30 = format_utc_timestamp(dt_30)

            act_00 = actuals_map.get(ts_start)
            act_30 = actuals_map.get(ts_30)

            # Energy-weighted average power across the 1-hour interval
            actual_mw = None
            if act_00 and act_30:
                actual_mw = round((act_00["generation"] + act_30["generation"]) / 2.0, 2)
                total_actuals_used += 2
            elif act_00:
                actual_mw = act_00["generation"]
                total_actuals_used += 1
            elif act_30:
                actual_mw = act_30["generation"]
                total_actuals_used += 1

            fc = forecasts_map.get(ts_start)
            fc_val = fc["generation"] if fc else None
            fc_pub = fc["publish_time"] if fc else None

            if actual_mw is not None and fc_val is not None:
                status = "matched"
                signed_err = round(fc_val - actual_mw, 2)
                abs_err = round(abs(signed_err), 2)
                matched_pairs.append((fc_val, actual_mw))
            elif actual_mw is not None:
                status = "missing_forecast"
                signed_err = None
                abs_err = None
                matched_pairs.append((None, actual_mw))
            elif fc_val is not None:
                status = "missing_actual"
                signed_err = None
                abs_err = None
                matched_pairs.append((fc_val, None))
            else:
                # Interval completely missing both actual and forecast
                status = "missing_both"
                signed_err = None
                abs_err = None

            observations.append({
                "delivery_timestamp": ts_start,
                "delivery_end_timestamp": ts_end,
                "forecast_publish_time": fc_pub,
                "forecast_mw": fc_val,
                "actual_mw": actual_mw,
                "signed_error": signed_err,
                "absolute_error": abs_err,
                "status": status,
            })

            dt_cur = dt_next

        total_expected_intervals = len(observations)
        return observations, matched_pairs, total_actuals_used, total_expected_intervals

    elif resolution == "half_hourly":
        # Half-Hourly Resolution: Step through 30 minutes at a time
        while dt_cur < dt_end:
            ts_start = format_utc_timestamp(dt_cur)
            dt_next = dt_cur + timedelta(minutes=30)
            ts_end = format_utc_timestamp(dt_next)

            # Hour start for looking up the Day-Ahead hourly block forecast
            dt_hour = dt_cur.replace(minute=0, second=0)
            ts_hour = format_utc_timestamp(dt_hour)

            act = actuals_map.get(ts_start)
            actual_mw = act["generation"] if act else None
            if act:
                total_actuals_used += 1

            fc = forecasts_map.get(ts_hour)
            fc_val = fc["generation"] if fc else None
            fc_pub = fc["publish_time"] if fc else None

            if actual_mw is not None and fc_val is not None:
                status = "matched"
                signed_err = round(fc_val - actual_mw, 2)
                abs_err = round(abs(signed_err), 2)
                matched_pairs.append((fc_val, actual_mw))
            elif actual_mw is not None:
                status = "missing_forecast"
                signed_err = None
                abs_err = None
                matched_pairs.append((None, actual_mw))
            elif fc_val is not None:
                status = "missing_actual"
                signed_err = None
                abs_err = None
                matched_pairs.append((fc_val, None))
            else:
                status = "missing_both"
                signed_err = None
                abs_err = None

            observations.append({
                "delivery_timestamp": ts_start,
                "delivery_end_timestamp": ts_end,
                "forecast_publish_time": fc_pub,
                "forecast_mw": fc_val,
                "actual_mw": actual_mw,
                "signed_error": signed_err,
                "absolute_error": abs_err,
                "status": status,
            })

            dt_cur = dt_next

        total_expected_intervals = len(observations)
        return observations, matched_pairs, total_actuals_used, total_expected_intervals

    else:
        # Exact Timestamp Resolution (Unaggregated :00 only)
        filter_start_iso = f"{start_date}T00:00:00Z"
        filter_end_iso = f"{end_date}T23:59:59Z"
        all_timestamps = set(actuals_map.keys()).union(set(forecasts_map.keys()))
        all_timestamps = {ts for ts in all_timestamps if filter_start_iso <= ts <= filter_end_iso}
        sorted_timestamps = sorted(all_timestamps)

        for ts in sorted_timestamps:
            act = actuals_map.get(ts)
            fc = forecasts_map.get(ts)
            act_val = act["generation"] if act else None
            fc_val = fc["generation"] if fc else None
            fc_pub = fc["publish_time"] if fc else None

            if act_val is not None:
                total_actuals_used += 1

            if act_val is not None and fc_val is not None:
                status = "matched"
                signed_err = round(fc_val - act_val, 2)
                abs_err = round(abs(signed_err), 2)
                matched_pairs.append((fc_val, act_val))
            elif act_val is not None:
                status = "missing_forecast"
                signed_err = None
                abs_err = None
                matched_pairs.append((None, act_val))
            else:
                status = "missing_actual"
                signed_err = None
                abs_err = None
                matched_pairs.append((fc_val, None))

            dt_s = parse_utc_timestamp(ts)
            dt_e = dt_s + timedelta(minutes=30) if dt_s else None

            observations.append({
                "delivery_timestamp": ts,
                "delivery_end_timestamp": format_utc_timestamp(dt_e),
                "forecast_publish_time": fc_pub,
                "forecast_mw": fc_val,
                "actual_mw": act_val,
                "signed_error": signed_err,
                "absolute_error": abs_err,
                "status": status,
            })

        total_expected_intervals = len(observations)
        return observations, matched_pairs, total_actuals_used, total_expected_intervals
