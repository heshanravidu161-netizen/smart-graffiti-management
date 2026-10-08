"""
Automatic graffiti classification service.

Four trained AI models are used:

1. Graffiti detector
   - Detects graffiti
   - Produces bounding boxes and confidence scores
   - Estimates size using image coverage

2. Graffiti-style classifier
   - Predicts mural or tag

3. Offensive-content classifier
   - Predicts offensive or not_offensive

4. Surface-type classifier
   - Predicts the surface shown in the complete photograph

The classification process runs automatically after report submission.
Low-confidence results are marked for manual review.
"""

import os
import random
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
import requests
from ultralytics import YOLO

from app.services.harm_classifier import compute_harm_score


# ---------------------------------------------------------
# Project and model paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]


DETECTION_MODEL_PATH = (
    PROJECT_ROOT
    / "ml_pipeline"
    / "models"
    / "graffiti_detector"
    / "weights"
    / "best.pt"
)


STYLE_MODEL_PATH = (
    PROJECT_ROOT
    / "ml_pipeline"
    / "models"
    / "graffiti_style_classifier"
    / "weights"
    / "best.pt"
)


OFFENSIVE_MODEL_PATH = (
    PROJECT_ROOT
    / "ml_pipeline"
    / "models"
    / "graffiti_offensive_classifier_v2"
    / "weights"
    / "best.pt"
)


SURFACE_MODEL_PATH = (
    PROJECT_ROOT
    / "ml_pipeline"
    / "models"
    / "graffiti_surface_classifier_v2"
    / "weights"
    / "best.pt"
)


# The surface classifier uses different category names from
# the harm-scoring system. This mapping converts between them.
SURFACE_SCORING_MAP = {
    "community_facility": "community_facility",
    "fence": "private_fence",
    "other": "unknown",
    "pavement_or_footpath": "unknown",
    "public_signage": "public_signage",
    "shopfront": "commercial_shopfront",
    "wall_or_hoarding": "temporary_hoarding",
}


# ---------------------------------------------------------
# Thresholds
# ---------------------------------------------------------

# Approximate image-coverage thresholds.
# These represent image coverage, not actual square metres.
SMALL_THRESHOLD = 0.05
MEDIUM_THRESHOLD = 0.20


# Graffiti detection thresholds.
DETECTION_CONFIDENCE_THRESHOLD = 0.25
DETECTION_REVIEW_THRESHOLD = 0.50


# Classification review thresholds.
STYLE_REVIEW_THRESHOLD = 0.70
OFFENSIVE_REVIEW_THRESHOLD = 0.85
SURFACE_REVIEW_THRESHOLD = 0.70


# ---------------------------------------------------------
# Model cache
# ---------------------------------------------------------

# Models are loaded once and reused for later requests.
_detection_model = None
_style_model = None
_offensive_model = None
_surface_model = None


def load_model(
    current_model,
    model_path: Path,
    model_name: str,
) -> YOLO:
    """Load a YOLO model after checking that it exists."""

    if current_model is not None:
        return current_model

    if not model_path.exists():
        raise FileNotFoundError(
            f"{model_name} was not found: {model_path}"
        )

    return YOLO(str(model_path))


def get_detection_model() -> YOLO:
    """Load and return the graffiti-detection model."""

    global _detection_model

    _detection_model = load_model(
        _detection_model,
        DETECTION_MODEL_PATH,
        "Graffiti detection model",
    )

    return _detection_model


def get_style_model() -> YOLO:
    """Load and return the graffiti-style model."""

    global _style_model

    _style_model = load_model(
        _style_model,
        STYLE_MODEL_PATH,
        "Graffiti style model",
    )

    return _style_model


def get_offensive_model() -> YOLO:
    """Load and return the offensive-content model."""

    global _offensive_model

    _offensive_model = load_model(
        _offensive_model,
        OFFENSIVE_MODEL_PATH,
        "Offensive-content model",
    )

    return _offensive_model


def get_surface_model() -> YOLO:
    """Load and return the surface-type model."""

    global _surface_model

    _surface_model = load_model(
        _surface_model,
        SURFACE_MODEL_PATH,
        "Surface-type model",
    )

    return _surface_model


# ---------------------------------------------------------
# Image helpers
# ---------------------------------------------------------

def bucket_size(area_fraction: float) -> str:
    """Convert image coverage into a size category."""

    if area_fraction < SMALL_THRESHOLD:
        return "small"

    if area_fraction < MEDIUM_THRESHOLD:
        return "medium"

    return "large"


def download_image(image_url: str) -> str:
    """
    Download a report image into a temporary file.

    The caller must delete the temporary file after inference.
    """

    parsed_url = urlparse(image_url)

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError(
            "The image URL must use HTTP or HTTPS."
        )

    response = requests.get(
        image_url,
        timeout=30,
        stream=True,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        "",
    )

    if (
        content_type
        and not content_type.startswith("image/")
    ):
        raise ValueError(
            "The supplied URL did not return an image."
        )

    suffix = Path(parsed_url.path).suffix.lower()

    if suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        suffix = ".jpg"

    temporary_file = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    )

    try:
        downloaded_size = 0
        maximum_size = 20 * 1024 * 1024

        for chunk in response.iter_content(
            chunk_size=8192
        ):
            if not chunk:
                continue

            downloaded_size += len(chunk)

            if downloaded_size > maximum_size:
                raise ValueError(
                    "The image is larger than 20 MB."
                )

            temporary_file.write(chunk)

        temporary_file.close()

        return temporary_file.name

    except Exception:
        temporary_file.close()

        if os.path.exists(temporary_file.name):
            os.remove(temporary_file.name)

        raise

    finally:
        response.close()


def load_full_image(
    local_image_path: str,
) -> Image.Image:
    """Load the complete image for surface classification."""

    with Image.open(local_image_path) as source_image:
        image = source_image.convert("RGB")

        return image.copy()


def crop_detection(
    local_image_path: str,
    detection: dict,
) -> Image.Image:
    """Crop one detected graffiti region from the image."""

    bbox = detection["bbox"]

    with Image.open(local_image_path) as source_image:
        image = source_image.convert("RGB")

        image_width, image_height = image.size

        x1 = max(
            0,
            min(
                int(bbox["x1"]),
                image_width - 1,
            ),
        )

        y1 = max(
            0,
            min(
                int(bbox["y1"]),
                image_height - 1,
            ),
        )

        x2 = max(
            x1 + 1,
            min(
                int(bbox["x2"]),
                image_width,
            ),
        )

        y2 = max(
            y1 + 1,
            min(
                int(bbox["y2"]),
                image_height,
            ),
        )

        crop = image.crop(
            (x1, y1, x2, y2)
        )

        return crop.copy()


# ---------------------------------------------------------
# Graffiti detection
# ---------------------------------------------------------

def detect_graffiti(
    local_image_path: str,
) -> list[dict]:
    """Run the detector and return every graffiti detection."""

    model = get_detection_model()

    results = model.predict(
        source=local_image_path,
        conf=DETECTION_CONFIDENCE_THRESHOLD,
        verbose=False,
    )

    detections = []

    for result in results:
        image_height, image_width = result.orig_shape
        image_area = image_width * image_height

        if result.boxes is None:
            continue

        for box in result.boxes:
            x1, y1, x2, y2 = (
                box.xyxy[0].tolist()
            )

            box_width = max(
                0.0,
                x2 - x1,
            )

            box_height = max(
                0.0,
                y2 - y1,
            )

            box_area = box_width * box_height

            area_fraction = (
                box_area / image_area
                if image_area > 0
                else 0.0
            )

            confidence = float(
                box.conf[0].item()
            )

            detections.append(
                {
                    "class_name": "graffiti",
                    "confidence": round(
                        confidence,
                        3,
                    ),
                    "size_category": bucket_size(
                        area_fraction
                    ),
                    "area_fraction": round(
                        area_fraction,
                        4,
                    ),
                    "bbox": {
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                    },
                    "image_width": image_width,
                    "image_height": image_height,
                }
            )

    return detections


# ---------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------

def classify_with_model(
    model: YOLO,
    image: Image.Image,
) -> dict:
    """Run a YOLO image-classification model."""

    results = model.predict(
        source=image,
        verbose=False,
    )

    if not results:
        return {
            "category": "unknown",
            "confidence": 0.0,
        }

    result = results[0]

    if result.probs is None:
        return {
            "category": "unknown",
            "confidence": 0.0,
        }

    predicted_index = int(
        result.probs.top1
    )

    predicted_category = result.names[
        predicted_index
    ]

    confidence = float(
        result.probs.top1conf.item()
    )

    return {
        "category": predicted_category,
        "confidence": round(
            confidence,
            3,
        ),
    }


def classify_graffiti_style(
    graffiti_crop: Image.Image,
) -> dict:
    """Predict mural or tag from the graffiti crop."""

    return classify_with_model(
        get_style_model(),
        graffiti_crop,
    )


def classify_offensive_content(
    graffiti_crop: Image.Image,
) -> dict:
    """Predict offensive or not_offensive."""

    return classify_with_model(
        get_offensive_model(),
        graffiti_crop,
    )


def classify_surface_type(
    complete_image: Image.Image,
) -> dict:
    """
    Predict the surface type using the complete image.

    The complete image is used because the model requires
    the surrounding scene to identify the surface.
    """

    return classify_with_model(
        get_surface_model(),
        complete_image,
    )


# ---------------------------------------------------------
# Classification results
# ---------------------------------------------------------

def no_graffiti_result() -> dict:
    """
    Return a zero-score result when graffiti is not detected.

    The report is sent for manual review because the detector
    may have missed graffiti.
    """

    return {
        "id": random.randint(1000, 9999),
        "graffiti_detected": False,
        "surface_type": "not_applicable",
        "tag_category": "not_applicable",
        "location_type": "not_applicable",
        "size_category": "not_applicable",
        "detection_confidence": 0.0,
        "manual_review_required": True,
        "detections": [],
        "harm_score": 0,
        "severity_band": "None",
        "harm_breakdown": {},
        "model_version": (
            "det-v1+style-v1+off-v2+surface-v2"
        ),
    }


def classify_local_image(
    local_image_path: str,
    occurrence_count: int = 1,
) -> dict:
    """Run all trained models on a local image."""

    detections = detect_graffiti(
        local_image_path
    )

    if not detections:
        return no_graffiti_result()

    best_detection = max(
        detections,
        key=lambda item: item["confidence"],
    )

    detection_confidence = (
        best_detection["confidence"]
    )

    size_category = (
        best_detection["size_category"]
    )

    graffiti_crop = crop_detection(
        local_image_path,
        best_detection,
    )

    complete_image = load_full_image(
        local_image_path
    )

    try:
        style_result = classify_graffiti_style(
            graffiti_crop
        )

        offensive_result = (
            classify_offensive_content(
                graffiti_crop
            )
        )

        surface_result = classify_surface_type(
            complete_image
        )

    finally:
        graffiti_crop.close()
        complete_image.close()

    style_category = (
        style_result["category"]
    )

    style_confidence = (
        style_result["confidence"]
    )

    offensive_category = (
        offensive_result["category"]
    )

    offensive_confidence = (
        offensive_result["confidence"]
    )

    surface_type = (
        surface_result["category"]
    )

    surface_confidence = (
        surface_result["confidence"]
    )

    # Keep the raw surface prediction for display.
    # Only confident predictions affect the harm score.
    surface_type_for_scoring = "unknown"

    if surface_confidence >= SURFACE_REVIEW_THRESHOLD:
        surface_type_for_scoring = (
            SURFACE_SCORING_MAP.get(
                surface_type,
                "unknown",
            )
        )

    offensive_detected = (
        offensive_category == "offensive"
    )

    if offensive_detected:
        harm_content_category = (
            "offensive_content"
        )
    else:
        harm_content_category = (
            style_category
        )

    # Location classification is not trained yet.
    location_type = "unknown"

    # Store the detailed model results inside the best
    # detection so the dashboard can display them.
    best_detection["style_category"] = (
        style_category
    )

    best_detection["style_confidence"] = (
        style_confidence
    )

    best_detection["style_model_version"] = (
        "style-v1"
    )

    best_detection["offensive_category"] = (
        offensive_category
    )

    best_detection["offensive_confidence"] = (
        offensive_confidence
    )

    best_detection["offensive_content_detected"] = (
        offensive_detected
    )

    best_detection["offensive_model_version"] = (
        "off-v2"
    )

    best_detection["surface_type"] = (
        surface_type
    )

    best_detection["surface_confidence"] = (
        surface_confidence
    )

    best_detection["surface_type_for_scoring"] = (
        surface_type_for_scoring
    )

    best_detection["surface_prediction_accepted"] = (
        surface_confidence
        >= SURFACE_REVIEW_THRESHOLD
    )

    best_detection["surface_model_version"] = (
        "surface-v2"
    )

    harm_result = compute_harm_score(
        content_category=harm_content_category,
        surface_category=surface_type_for_scoring,
        location_category=location_type,
        size_category=size_category,
        occurrence_count=occurrence_count,
    )

    # Any uncertain or offensive result is flagged for
    # council review. Classification and scoring still finish.
    manual_review_required = any(
        [
            detection_confidence
            < DETECTION_REVIEW_THRESHOLD,

            style_confidence
            < STYLE_REVIEW_THRESHOLD,

            offensive_confidence
            < OFFENSIVE_REVIEW_THRESHOLD,

            surface_confidence
            < SURFACE_REVIEW_THRESHOLD,

            offensive_detected,
        ]
    )

    return {
        "id": random.randint(1000, 9999),
        "graffiti_detected": True,
        "surface_type": surface_type,
        "tag_category": harm_content_category,
        "location_type": location_type,
        "size_category": size_category,
        "detection_confidence": (
            detection_confidence
        ),
        "manual_review_required": (
            manual_review_required
        ),
        "detections": detections,
        "harm_score": harm_result["harm_score"],
        "severity_band": (
            harm_result["severity_band"]
        ),
        "harm_breakdown": (
            harm_result["breakdown"]
        ),
        "model_version": (
            "det-v1+style-v1+off-v2+surface-v2"
        ),
    }


def classify_image(
    image_url: str,
    occurrence_count: int = 1,
) -> dict:
    """Download and classify a report image."""

    temporary_path = download_image(
        image_url
    )

    try:
        return classify_local_image(
            temporary_path,
            occurrence_count=occurrence_count,
        )

    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
