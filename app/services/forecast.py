"""Pronóstico por regresión lineal simple (mínimos cuadrados), sin dependencias externas."""
from typing import Optional

from app.schemas import ForecastResponse


def linear_fit(values: list[float]) -> tuple[float, float, float]:
    n = len(values)
    xs = range(n)
    mx = (n - 1) / 2
    my = sum(values) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, values))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in values)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, values))
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return slope, intercept, r2


def forecast(values: list[float], horizon: int, critical_below: Optional[float]) -> ForecastResponse:
    slope, intercept, r2 = linear_fit(values)
    n = len(values)
    preds = [round(max(0.0, intercept + slope * (n + i)), 2) for i in range(horizon)]
    hours: Optional[float] = None
    if critical_below is not None and slope < 0:
        last = values[-1]
        if last <= critical_below:
            hours = 0.0
        else:
            hours = round((last - critical_below) / -slope, 1)
    trend = "ESTABLE" if abs(slope) < 0.05 else ("SUBE" if slope > 0 else "BAJA")
    return ForecastResponse(
        forecast=preds, slope=round(slope, 4), r2=round(r2, 3),
        hours_to_critical=hours, trend=trend,
    )
