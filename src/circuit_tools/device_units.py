"""Explicit current scaling at the cm-based 2D device/circuit boundary.

Use this only when the backend's native current has been established as A/cm
of out-of-plane width. The geometry's lateral gate length is not that width.
The returned amperes must not receive a second width multiplier in SPICE.
"""
from __future__ import annotations

import math

from .core import ValidationError


def current_per_cm_to_amperes(current_a_per_cm: float, width_m: float) -> float:
    """Scale signed native 2D current by a separately declared SI width."""
    for name, value in (("current_a_per_cm", current_a_per_cm), ("width_m", width_m)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValidationError(f"{name} must be a finite number")
    if width_m <= 0:
        raise ValidationError("width_m must be positive")
    current_a = current_a_per_cm * (100.0 * width_m)
    if not math.isfinite(current_a):
        raise ValidationError("scaled current exceeds the finite numeric range")
    return current_a
