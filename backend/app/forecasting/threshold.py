from datetime import datetime, timedelta
from typing import Optional, Tuple

def calculate_threshold_crossing(
    current_fill: float,
    threshold: float,
    hourly_growth_rate: float,
    current_time: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[float]]:
    """
    Calculates the exact projected timestamp and hours remaining until a bin
    crosses its operational collection threshold (e.g., 85%).
    Returns: (projected_crossing_datetime, hours_remaining)
    """
    now = current_time or datetime.utcnow()

    # Already exceeded threshold
    if current_fill >= threshold:
        return now, 0.0

    # If growth rate is negligible or negative, it will not cross
    if hourly_growth_rate <= 0.01:
        return None, None

    fill_gap = threshold - current_fill
    hours_remaining = fill_gap / hourly_growth_rate

    crossing_time = now + timedelta(hours=hours_remaining)
    return crossing_time, round(hours_remaining, 1)
