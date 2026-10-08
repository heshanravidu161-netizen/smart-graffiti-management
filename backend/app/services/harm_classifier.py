"""
Automatic graffiti harm-scoring framework.

Five criteria are scored using values of 1, 3 or 5.
Each value is multiplied by its proposal-defined weight.
The weighted total is converted to a 1-15 harm score.
"""


WEIGHTS = {
    "content": 3,
    "location_visibility": 2,
    "surface_type": 2,
    "size_coverage": 1,
    "recurrence": 2,
}


CONTENT_SCORES = {
    "mural": 1,
    "stencil": 1,
    "tag": 3,
    "offensive_content": 5,
    "other": 3,
    "unknown": 3,
}


# Includes the original proposal categories and the exact
# categories produced by the trained surface classifier.
SURFACE_SCORES = {
    # Trained classifier categories
    "fence": 1,
    "wall_or_hoarding": 1,
    "pavement_or_footpath": 3,
    "public_signage": 3,
    "shopfront": 3,
    "community_facility": 5,
    "other": 3,
    "unknown": 3,

    # Original proposal category names
    "private_fence": 1,
    "temporary_hoarding": 1,
    "commercial_shopfront": 3,
    "heritage_building": 5,
    "public_monument": 5,
}


LOCATION_SCORES = {
    "laneway": 1,
    "rear_wall": 1,
    "side_street": 3,
    "main_street": 5,
    "school_zone": 5,
    "transport_hub": 5,
    "other": 3,
    "unknown": 3,
}


SIZE_SCORES = {
    "small": 1,
    "medium": 3,
    "large": 5,
}


def recurrence_score(
    occurrence_count: int,
) -> int:
    """Convert occurrence count into 1, 3 or 5."""

    if occurrence_count <= 1:
        return 1

    if occurrence_count == 2:
        return 3

    return 5


def compute_harm_score(
    content_category: str,
    surface_category: str,
    location_category: str,
    size_category: str,
    occurrence_count: int = 1,
) -> dict:
    """Calculate and explain the automatic harm score."""

    content = CONTENT_SCORES.get(
        content_category,
        3,
    )

    surface = SURFACE_SCORES.get(
        surface_category,
        3,
    )

    location = LOCATION_SCORES.get(
        location_category,
        3,
    )

    size = SIZE_SCORES.get(
        size_category,
        3,
    )

    recurrence = recurrence_score(
        occurrence_count
    )

    breakdown = {
        "content": {
            "category": content_category,
            "raw": content,
            "weight": WEIGHTS["content"],
            "weighted": (
                content * WEIGHTS["content"]
            ),
        },
        "surface_type": {
            "category": surface_category,
            "raw": surface,
            "weight": WEIGHTS["surface_type"],
            "weighted": (
                surface
                * WEIGHTS["surface_type"]
            ),
        },
        "location_visibility": {
            "category": location_category,
            "raw": location,
            "weight": (
                WEIGHTS["location_visibility"]
            ),
            "weighted": (
                location
                * WEIGHTS[
                    "location_visibility"
                ]
            ),
        },
        "size_coverage": {
            "category": size_category,
            "raw": size,
            "weight": WEIGHTS["size_coverage"],
            "weighted": (
                size * WEIGHTS["size_coverage"]
            ),
        },
        "recurrence": {
            "category": occurrence_count,
            "raw": recurrence,
            "weight": WEIGHTS["recurrence"],
            "weighted": (
                recurrence * WEIGHTS["recurrence"]
            ),
        },
    }

    total_weighted = sum(
        item["weighted"]
        for item in breakdown.values()
    )

    max_possible = (
        5 * sum(WEIGHTS.values())
    )

    harm_score = round(
        (total_weighted / max_possible) * 15
    )

    harm_score = max(
        1,
        min(15, harm_score),
    )

    if harm_score <= 5:
        severity_band = "Low"

    elif harm_score <= 10:
        severity_band = "Medium"

    else:
        severity_band = "High"

    return {
        "harm_score": harm_score,
        "severity_band": severity_band,
        "breakdown": breakdown,
        "total_weighted": total_weighted,
        "max_possible": max_possible,
    }
