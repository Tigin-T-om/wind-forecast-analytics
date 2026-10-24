"""Accuracy metrics calculation module using Python standard library.

Provides calculations for Mean Absolute Error (MAE), Root Mean Squared Error (RMSE),
and Forecast Bias (mean signed error: forecast - actual).
Pandas is intentionally excluded in adherence to system security restrictions.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def calculate_metrics(
    pairs: List[Tuple[Optional[float], Optional[float]]],
    total_expected_intervals: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate MAE, RMSE, and Bias over valid matched (forecast, actual) pairs.

    Definition:
        error = forecast - actual
        MAE   = mean(|error|)
        RMSE  = sqrt(mean(error^2))
        Bias  = mean(error)  [Positive bias = forecast overestimates actual]

    Args:
        pairs: List of (forecast_mw, actual_mw) tuples.
        total_expected_intervals: Optional expected interval count for coverage calculation.

    Returns:
        Dictionary with mae, rmse, bias, matched_count, and coverage_percentage.
    """
    valid_signed_errors: List[float] = []
    valid_abs_errors: List[float] = []
    valid_squared_errors: List[float] = []

    for item in pairs:
        if not item or len(item) < 2:
            continue
        fc, act = item[0], item[1]
        if fc is None or act is None:
            continue
        try:
            fc_val = float(fc)
            act_val = float(act)
        except (ValueError, TypeError):
            continue

        if math.isnan(fc_val) or math.isnan(act_val):
            continue

        err = fc_val - act_val
        valid_signed_errors.append(err)
        valid_abs_errors.append(abs(err))
        valid_squared_errors.append(err * err)

    n = len(valid_signed_errors)

    if n == 0:
        return {
            "mae": None,
            "rmse": None,
            "bias": None,
            "matched_count": 0,
            "coverage_percentage": 0.0 if total_expected_intervals and total_expected_intervals > 0 else None,
            "unit": "MW",
        }

    mae = sum(valid_abs_errors) / n
    mse = sum(valid_squared_errors) / n
    rmse = math.sqrt(mse)
    bias = sum(valid_signed_errors) / n

    coverage = None
    if total_expected_intervals and total_expected_intervals > 0:
        coverage = round((n / total_expected_intervals) * 100.0, 1)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "matched_count": n,
        "coverage_percentage": coverage,
        "unit": "MW",
    }
