"""Scale-aware zero-relief normalization; never changes the BREP."""

from __future__ import annotations

import math


def epsilon_zero(source_volume_mm3: float, epsilon_abs_mm3: float, epsilon_rel: float = 1e-6) -> float:
    if not all(math.isfinite(x) and x >= 0 for x in (source_volume_mm3, epsilon_abs_mm3, epsilon_rel)):
        raise ValueError("nonfinite or negative zero-rule parameter")
    return max(epsilon_abs_mm3, epsilon_rel * source_volume_mm3)


def normalize_removed_volume(delta_mm3: float, epsilon_mm3: float):
    """Inclusive negative boundary; positive relief is never normalized."""
    if not math.isfinite(delta_mm3) or not math.isfinite(epsilon_mm3) or epsilon_mm3 < 0:
        raise ValueError("invalid relief measurement or epsilon")
    if delta_mm3 >= 0:
        return {"raw_removed_volume_mm3": delta_mm3,
                "normalized_removed_volume_mm3": delta_mm3,
                "normalization_applied": False, "status": "NONNEGATIVE_RETAINED"}
    if delta_mm3 >= -epsilon_mm3:
        return {"raw_removed_volume_mm3": delta_mm3,
                "normalized_removed_volume_mm3": 0.0,
                "normalization_applied": True,
                "status": "ZERO_RELIEF_WITHIN_ENGINEERING_TOLERANCE"}
    return {"raw_removed_volume_mm3": delta_mm3,
            "normalized_removed_volume_mm3": None,
            "normalization_applied": False,
            "status": "WITNESS_NUMERICALLY_UNSTABLE"}
