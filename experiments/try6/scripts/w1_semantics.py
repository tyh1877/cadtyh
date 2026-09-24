"""Frozen D1 relief-category and engineering-stability bookkeeping only."""

from __future__ import annotations


def relief_category(ratio: float) -> str:
    if ratio < 0:
        raise ValueError("negative relief ratio")
    if ratio <= 0.05:
        return "SMALL_RELIEF"
    if ratio <= 0.15:
        return "MODERATE_RELIEF"
    return "LARGE_RELIEF"


def sensitivity_category(ratios):
    if not ratios:
        return {"interval": None, "category": None, "category_status": "NOT_MEASURABLE"}
    low, high = min(ratios), max(ratios)
    low_category, high_category = relief_category(low), relief_category(high)
    return {"interval": [low, high],
            "category": low_category if low_category == high_category else None,
            "category_status": ("ROBUST" if low_category == high_category
                                else "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS"),
            "endpoint_categories": [low_category, high_category],
            "is_statistical_confidence_interval": False}


def topology_class(state: str, solid_count: int) -> str:
    if state == "EFFECTIVELY_EMPTY" and solid_count == 0:
        return "EFFECTIVELY_EMPTY"
    if state == "VALID_SINGLE_SOLID" and solid_count == 1:
        return "CONNECTED_SINGLE_SOLID"
    if state == "VALID_MULTI_SOLID" and solid_count > 1:
        return "DISCONNECTED_MULTI_SOLID"
    raise ValueError("inconsistent state/solid count")
