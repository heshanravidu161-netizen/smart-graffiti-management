"""
Automatic graffiti classification service.

Four trained AI models are used:

1. Graffiti detector
   - Detects graffiti
   - Produces bounding boxes and confidence scores
   - Uses tiled fallback detection for smaller graffiti

2. Graffiti-style classifier
   - Predicts mural or tag


3. Offensive-content classifier
   - Predicts offensive or not_offensive

4. Surface-type classifier
   - Uses an expanded graffiti-region crop
   - Predicts the surface surrounding the graffiti

Low-confidence and tiled-fallback results are marked for manual review.
"""

import gc
import os
import random
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
import requests
import torch
from ultralytics import YOLO

from app.services.harm_classifier import compute_harm_score


# --------------------------------------------------------
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
    / "graffiti_style_classifier_v2"
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
# Thresholds and settings
# --------------------------------------------------------

# Image coverage, not actual square metres.
SMALL_THRESHOLD = 0.05
MEDIUM_THRESHOLD = 0.20

DETECTION_CONFIDENCE_THRESHOLD = 0.25
DETECTION_REVIEW_THRESHOLD = 0.50

STYLE_REVIEW_THRESHOLD = 0.70
OFFENSIVE_REVIEW_THRESHOLD = 0.85
SURFACE_REVIEW_THRESHOLD = 0.70

# Tiled detector settings.
TILE_SIZE_FRACTION = 0.65
DUPLICATE_OVERLAP_THRESHOLD = 0.45

# The surface crop is expanded by 35% around each side of
# the detected graffiti bounding box.
SURFACE_CONTEXT_EXPANSION = 0.35


# ---------------------------------------------------------
# Low-memory model loading
# ---------------------------------------------------------

def load_model(
    model_path: Path,
    model_name: str,
) -> YOLO:
    """Load one YOLO model after checking that it exists."""

    if not model_path.exists():
        raise FileNotFoundError(
            f"{model_name} was not found: {model_path}"
        )

    return YOLO(str(model_path))


def release_model(model=None) -> None:
    """Release a model and return unused memory."""

    if model is not None:
        try:
            del model
        except Exception:
            pass

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    if hasattr(torch, "mps"):
        try:
            torch.mps.empty_cache()
        except Exception:
            pass

    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)

    except Exception:
        pass


def get_detection_model() -> YOLO:
    """Load a fresh graffiti-detection model."""

    return load_model(
        DETECTION_MODEL_PATH,
        "Graffiti detection model",
    )


def get_style_model() -> YOLO:
    """Load a fresh graffiti-style model."""

    return load_model(
        STYLE_MODEL_PATH,
        "Graffiti style model",
    )


def get_offensive_model() -> YOLO:
    """Load a fresh offensive-content model."""

    return load_model(
        OFFENSIVE_MODEL_PATH,
        "Offensive-content model",
    )


def get_surface_model() -> YOLO:
    """Load a fresh surface-type model."""

    return load_model(
        SURFACE_MODEL_PATH,
        "Surface-type model",
    )


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

    The caller must delete the returned temporary file.
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
            chunk_size=8192,
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
    """Load the complete image as RGB."""

    with Image.open(local_image_path) as source_image:
        image = source_image.convert("RGB")

        return image.copy()


def crop_detection(
    local_image_path: str,
    detection: dict,
) -> Image.Image:
    """Crop one detected graffiti region."""

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


def crop_surface_context(
    local_image_path: str,
    detection: dict,
    expansion_fraction: float = (
        SURFACE_CONTEXT_EXPANSION
    ),
) -> Image.Image:
    """
    Crop the graffiti together with its surrounding surface.

    The expanded crop gives the surface model enough local context
    while reducing unrelated content elsewhere in the photograph.
    """

    bbox = detection["bbox"]

    with Image.open(local_image_path) as source_image:
        image = source_image.convert("RGB")

        image_width, image_height = image.size

        box_width = max(
            1.0,
            bbox["x2"] - bbox["x1"],
        )

        box_height = max(
            1.0,
            bbox["y2"] - bbox["y1"],
        )

        horizontal_expansion = (
            box_width * expansion_fraction
        )

        vertical_expansion = (
            box_height * expansion_fraction
        )

        x1 = max(
            0,
            int(
                bbox["x1"]
                - horizontal_expansion
            ),
        )

        y1 = max(
            0,
            int(
                bbox["y1"]
                - vertical_expansion
            ),
        )

        x2 = min(
            image_width,
            int(
                bbox["x2"]
                + horizontal_expansion
            ),
        )

        y2 = min(
            image_height,
            int(
                bbox["y2"]
                + vertical_expansion
            ),
        )

        x2 = max(x1 + 1, x2)
        y2 = max(y1 + 1, y2)

        surface_context = image.crop(
            (x1, y1, x2, y2)
        )

        return surface_context.copy()


# ---------------------------------------------------------
# Graffiti detection
# ---------------------------------------------------------

def bounding_box_iou(
    first_box: dict,
    second_box: dict,
) -> float:
    """Calculate overlap between two bounding boxes."""

    intersection_x1 = max(
        first_box["x1"],
        second_box["x1"],
    )

    intersection_y1 = max(
        first_box["y1"],
        second_box["y1"],
    )

    intersection_x2 = min(
        first_box["x2"],
        second_box["x2"],
    )

    intersection_y2 = min(
        first_box["y2"],
        second_box["y2"],
    )

    intersection_width = max(
        0.0,
        intersection_x2 - intersection_x1,
    )

    intersection_height = max(
        0.0,
        intersection_y2 - intersection_y1,
    )

    intersection_area = (
        intersection_width
        * intersection_height
    )

    first_width = max(
        0.0,
        first_box["x2"] - first_box["x1"],
    )

    first_height = max(
        0.0,
        first_box["y2"] - first_box["y1"],
    )

    second_width = max(
        0.0,
        second_box["x2"] - second_box["x1"],
    )

    second_height = max(
        0.0,
        second_box["y2"] - second_box["y1"],
    )

    first_area = first_width * first_height
    second_area = second_width * second_height

    union_area = (
        first_area
        + second_area
        - intersection_area
    )

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def remove_duplicate_detections(
    detections: list[dict],
    overlap_threshold: float = (
        DUPLICATE_OVERLAP_THRESHOLD
    ),
) -> list[dict]:
    """
    Remove repeated detections created by overlapping tiles.

    The highest-confidence detection is retained.
    """

    sorted_detections = sorted(
        detections,
        key=lambda item: item["confidence"],
        reverse=True,
    )

    accepted_detections = []

    for detection in sorted_detections:
        duplicate = any(
            bounding_box_iou(
                detection["bbox"],
                accepted["bbox"],
            ) >= overlap_threshold
            for accepted in accepted_detections
        )

        if not duplicate:
            accepted_detections.append(
                detection
            )

    return accepted_detections


def extract_detections(
    results,
    image_width: int,
    image_height: int,
    offset_x: int = 0,
    offset_y: int = 0,
    detection_method: str = "full_image",
) -> list[dict]:
    """
    Convert YOLO results into complete-image coordinates.

    Tile offsets are added when a prediction came from a cropped
    section of the original image.
    """

    detections = []
    image_area = image_width * image_height

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            local_x1, local_y1, local_x2, local_y2 = (
                box.xyxy[0].tolist()
            )

            x1 = max(
                0.0,
                min(
                    local_x1 + offset_x,
                    float(image_width),
                ),
            )

            y1 = max(
                0.0,
                min(
                    local_y1 + offset_y,
                    float(image_height),
                ),
            )

            x2 = max(
                x1,
                min(
                    local_x2 + offset_x,
                    float(image_width),
                ),
            )

            y2 = max(
                y1,
                min(
                    local_y2 + offset_y,
                    float(image_height),
                ),
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
                    "detection_method": (
                        detection_method
                    ),
                }
            )

    return detections


def detect_graffiti(
    local_image_path: str,
) -> list[dict]:
    """
    Detect graffiti using full-image and tiled inference.

    Tiled inference runs only when the full-image attempt returns
    no detections.
    """

    model = get_detection_model()
    complete_image = None

    try:
        complete_image = load_full_image(
            local_image_path
        )

        image_width, image_height = (
            complete_image.size
        )

        results = model.predict(
            source=complete_image,
            conf=DETECTION_CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        detections = extract_detections(
            results=results,
            image_width=image_width,
            image_height=image_height,
            detection_method="full_image",
        )

        del results

        if detections:
            return remove_duplicate_detections(
                detections
            )

        print(
            "No graffiti found in the complete image. "
            "Running tiled fallback detection..."
        )

        tile_width = max(
            1,
            int(
                image_width
                * TILE_SIZE_FRACTION
            ),
        )

        tile_height = max(
            1,
            int(
                image_height
                * TILE_SIZE_FRACTION
            ),
        )

        x_positions = sorted(
            {
                0,
                max(
                    0,
                    image_width - tile_width,
                ),
            }
        )

        y_positions = sorted(
            {
                0,
                max(
                    0,
                    image_height - tile_height,
                ),
            }
        )

        tiled_detections = []

        for offset_y in y_positions:
            for offset_x in x_positions:
                tile = complete_image.crop(
                    (
                        offset_x,
                        offset_y,
                        offset_x + tile_width,
                        offset_y + tile_height,
                    )
                )

                try:
                    tile_results = model.predict(
                        source=tile,
                        conf=(
                            DETECTION_CONFIDENCE_THRESHOLD
                        ),
                        verbose=False,
                    )

                    tile_detections = (
                        extract_detections(
                            results=tile_results,
                            image_width=image_width,
                            image_height=image_height,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            detection_method=(
                                "tiled_fallback"
                            ),
                        )
                    )

                    tiled_detections.extend(
                        tile_detections
                    )

                    del tile_results

                finally:
                    tile.close()

        filtered_detections = (
            remove_duplicate_detections(
                tiled_detections
            )
        )

        if filtered_detections:
            print(
                "Tiled fallback detected "
                f"{len(filtered_detections)} "
                "graffiti region(s)."
            )

        else:
            print(
                "Tiled fallback found no graffiti."
            )

        return filtered_detections

    finally:
        if complete_image is not None:
            complete_image.close()

        release_model(model)


# ---------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------

def classify_with_model(
    model: YOLO,
    image: Image.Image,
) -> dict:
    """Run a YOLO image-classification model."""

    try:
        results = model.predict(
            source=image,
            verbose=False,
        )

        if not results or results[0].probs is None:
            prediction = {
                "category": "unknown",
                "confidence": 0.0,
            }

        else:
            result = results[0]

            predicted_index = int(
                result.probs.top1
            )

            prediction = {
                "category": (
                    result.names[predicted_index]
                ),
                "confidence": round(
                    float(
                        result.probs.top1conf.item()
                    ),
                    3,
                ),
            }

        del results

        return prediction

    finally:
        release_model(model)


def classify_graffiti_style(
    graffiti_crop: Image.Image,
) -> dict:
    """Predict mural or tag."""

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
    surface_context_image: Image.Image,
) -> dict:
    """
    Predict the surface type using local context surrounding
    the detected graffiti.
    """

    return classify_with_model(
        get_surface_model(),
        surface_context_image,
    )


# ---------------------------------------------------------
# Classification results
# ---------------------------------------------------------

def no_graffiti_result() -> dict:
    """Return a zero-score result when graffiti is not detected."""

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
            "det-v1-tiled+style-v2+off-v2+surface-v2"
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

    detection_method = best_detection.get(
        "detection_method",
        "full_image",
    )

    graffiti_crop = crop_detection(
        local_image_path,
        best_detection,
    )

    surface_context_image = crop_surface_context(
        local_image_path,
        best_detection,
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
            surface_context_image
        )

    finally:
        graffiti_crop.close()
        surface_context_image.close()

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

    # Retain the raw surface prediction for display.
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

    # Location is added by classification_workflow.py.
    location_type = "unknown"

    best_detection["style_category"] = (
        style_category
    )

    best_detection["style_confidence"] = (
        style_confidence
    )

    best_detection["style_model_version"] = (
        "style-v2"
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

    best_detection["surface_input_method"] = (
        "expanded_graffiti_context"
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

    manual_review_required = any(
        [
            detection_confidence
            < DETECTION_REVIEW_THRESHOLD,

            detection_method
            == "tiled_fallback",

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
            "det-v1-tiled+style-v2+off-v2+surface-v2"
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
