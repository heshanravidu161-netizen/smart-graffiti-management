"""
Classification service — the seam between your backend and your trained AI model.

Right now this returns a hardcoded placeholder so the rest of the system can be
built and tested end-to-end without a model. Once ml_pipeline/ produces a
trained model, load it here and replace the placeholder logic.
"""

import random

_SURFACE_TYPES = ["brick_wall", "metal_shutter", "signage", "concrete_pillar"]
_TAG_CATEGORIES = ["tag", "stencil", "mural", "offensive_content"]


def classify_image(image_url: str) -> dict:
    """PLACEHOLDER — returns random-ish plausible output. Replace with a real
    model call once ml_pipeline has a trained model to load."""
    return {
        "id": random.randint(1000, 9999),
        "surface_type": random.choice(_SURFACE_TYPES),
        "tag_category": random.choice(_TAG_CATEGORIES),
        "detection_confidence": round(random.uniform(0.6, 0.95), 2),
        "harm_score": compute_harm_score(random.choice(_TAG_CATEGORIES)),
        "model_version": "placeholder-v0",
    }


def compute_harm_score(tag_category: str) -> int:
    """Rough placeholder mapping — replace with your team's real Graffiti Harm
    Classification framework logic from Section 3.2 of your proposal."""
    mapping = {
        "tag": 2,
        "stencil": 1,
        "mural": 1,
        "offensive_content": 5,
    }
    return mapping.get(tag_category, 3)
