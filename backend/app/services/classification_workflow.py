"""
Automatic report-classification workflow.

After a report is saved, this service runs the image models,
checks visual recurrence and location, calculates the harm score,
and saves the complete result.
"""

from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from app.database import SessionLocal
from app.models.db_models import Classification, Report
from app.services import classification_service
from app.services.harm_classifier import compute_harm_score
from app.services.image_similarity import compare_images
from app.services.location_classifier import classify_location


# Reports must be within this distance before their images
# are checked for visual similarity.
RECURRENCE_RADIUS_METRES = 50.0

# Only reports submitted during this recent time window can be
# counted as repeated occurrences.
RECURRENCE_WINDOW_DAYS = 90


def distance_in_metres(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """Calculate the distance between two GPS coordinates."""

    earth_radius_metres = 6_371_000

    latitude_1_radians = radians(latitude_1)
    latitude_2_radians = radians(latitude_2)

    latitude_difference = radians(
        latitude_2 - latitude_1
    )

    longitude_difference = radians(
        longitude_2 - longitude_1
    )

    haversine_value = (
        sin(latitude_difference / 2) ** 2
        + cos(latitude_1_radians)
        * cos(latitude_2_radians)
        * sin(longitude_difference / 2) ** 2
    )

    angular_distance = 2 * asin(
        sqrt(haversine_value)
    )

    return earth_radius_metres * angular_distance


def empty_recurrence_details() -> dict:
    """
    Return the default recurrence result.

    This result is used when graffiti was not detected or when no
    visually similar nearby report was found.
    """

    return {
        "occurrence_count": 1,
        "radius_metres": RECURRENCE_RADIUS_METRES,
        "time_window_days": RECURRENCE_WINDOW_DAYS,
        "similar_report_count": 0,
        "matched_reports": [],
        "repeated_graffiti_detected": False,
        "similarity_model_version": "similarity-v1",
    }


def calculate_recurrence_details(
    db,
    current_report: Report,
) -> dict:
    """
    Find visually similar earlier graffiti reports within 50 metres
    and the previous 90 days.

    A report is treated as a recurrence only when:

    1. The earlier report is within 50 metres.
    2. It was submitted during the previous 90 days.
    3. Graffiti was detected in the earlier report.
    4. The two report images pass the visual-similarity check.

    Only two earlier matches are required because the harm framework
    uses its maximum recurrence score for three or more occurrences.
    """

    recurrence_window_start = (
        current_report.submitted_at
        - timedelta(days=RECURRENCE_WINDOW_DAYS)
    )

    previous_reports = (
        db.query(Report)
        .join(
            Classification,
            Classification.report_id == Report.id,
        )
        .filter(
            Report.id != current_report.id,
            Report.submitted_at
            >= recurrence_window_start,
            Report.submitted_at
            < current_report.submitted_at,
            Classification.graffiti_detected.is_(True),
        )
        .order_by(Report.submitted_at.desc())
        .all()
    )

    matched_reports = []
    checked_report_ids = set()

    for previous_report in previous_reports:
        # A report can have more than one saved classification.
        # Avoid checking the same report more than once.
        if previous_report.id in checked_report_ids:
            continue

        checked_report_ids.add(previous_report.id)

        if (
            previous_report.latitude is None
            or previous_report.longitude is None
            or current_report.latitude is None
            or current_report.longitude is None
        ):
            continue

        distance = distance_in_metres(
            current_report.latitude,
            current_report.longitude,
            previous_report.latitude,
            previous_report.longitude,
        )

        # Do not download and compare images when the reports
        # are outside the recurrence radius.
        if distance > RECURRENCE_RADIUS_METRES:
            continue

        try:
            comparison = compare_images(
                current_report.image_url,
                previous_report.image_url,
            )
        except Exception as error:
            print(
                "Similarity check failed between "
                f"report #{current_report.id} and "
                f"report #{previous_report.id}: {error}"
            )
            continue

        print(
            f"Similarity check: report "
            f"#{current_report.id} versus "
            f"report #{previous_report.id}: "
            f"similar={comparison['visually_similar']}, "
            f"hash={comparison['hash_similarity']}, "
            f"features="
            f"{comparison['good_feature_matches']}."
        )

        if comparison["visually_similar"]:
            matched_reports.append(
                {
                    "report_id": int(previous_report.id),
                    "submitted_at": (
                        previous_report.submitted_at.isoformat()
                    ),
                    "distance_metres": float(
                        round(distance, 1)
                    ),
                    "hash_similarity": float(
                        comparison["hash_similarity"]
                    ),
                    "feature_similarity": float(
                        comparison["feature_similarity"]
                    ),
                    "good_feature_matches": int(
                        comparison[
                            "good_feature_matches"
                        ]
                    ),
                }
            )

        # Two earlier matches plus the current report equals
        # three occurrences, which is the maximum scoring band.
        if len(matched_reports) >= 2:
            break

    occurrence_count = min(
        3,
        1 + len(matched_reports),
    )

    return {
        "occurrence_count": occurrence_count,
        "radius_metres": RECURRENCE_RADIUS_METRES,
        "time_window_days": RECURRENCE_WINDOW_DAYS,
        "window_start": (
            recurrence_window_start.isoformat()
        ),
        "similar_report_count": len(matched_reports),
        "matched_reports": matched_reports,
        "repeated_graffiti_detected": (
            len(matched_reports) > 0
        ),
        "similarity_model_version": "similarity-v1",
    }


def calculate_occurrence_count(
    db,
    current_report: Report,
) -> int:
    """
    Return only the occurrence count.

    This compatibility function can still be used by existing tests.
    """

    recurrence_details = calculate_recurrence_details(
        db,
        current_report,
    )

    return recurrence_details["occurrence_count"]


def add_location_result(
    result: dict,
    latitude: float,
    longitude: float,
    occurrence_count: int,
) -> dict:
    """
    Add automatic GPS location classification and recalculate
    the harm score using location and recurrence.
    """

    if not result["graffiti_detected"]:
        return result

    location_result = classify_location(
        latitude,
        longitude,
    )

    raw_location_type = location_result[
        "location_type"
    ]

    if location_result["accepted_for_scoring"]:
        location_type_for_scoring = raw_location_type
    else:
        location_type_for_scoring = "unknown"

    best_detection = max(
        result["detections"],
        key=lambda item: item["confidence"],
    )

    best_detection["location_type"] = (
        raw_location_type
    )

    best_detection["location_confidence"] = (
        location_result["confidence"]
    )

    best_detection["location_type_for_scoring"] = (
        location_type_for_scoring
    )

    best_detection["location_prediction_accepted"] = (
        location_result["accepted_for_scoring"]
    )

    best_detection["location_map_category"] = (
        location_result["map_category"]
    )

    best_detection["location_map_type"] = (
        location_result["map_type"]
    )

    best_detection["location_display_name"] = (
        location_result["display_name"]
    )

    best_detection["location_reason"] = (
        location_result["reason"]
    )

    best_detection["location_model_version"] = (
        location_result["version"]
    )

    surface_type_for_scoring = best_detection.get(
        "surface_type_for_scoring",
        "unknown",
    )

    harm_result = compute_harm_score(
        content_category=result["tag_category"],
        surface_category=surface_type_for_scoring,
        location_category=location_type_for_scoring,
        size_category=result["size_category"],
        occurrence_count=occurrence_count,
    )

    result["location_type"] = raw_location_type
    result["harm_score"] = harm_result["harm_score"]
    result["severity_band"] = harm_result[
        "severity_band"
    ]
    result["harm_breakdown"] = harm_result[
        "breakdown"
    ]

    result["manual_review_required"] = (
        result["manual_review_required"]
        or not location_result[
            "accepted_for_scoring"
        ]
    )

    if "location-osm-v1" not in result["model_version"]:
        result["model_version"] += (
            "+location-osm-v1"
        )

    print(
        "Automatic location classification: "
        f"{raw_location_type}, "
        f"confidence "
        f"{location_result['confidence']:.3f}, "
        f"accepted: "
        f"{location_result['accepted_for_scoring']}."
    )

    return result


def add_recurrence_result(
    result: dict,
    recurrence_details: dict,
) -> dict:
    """
    Add recurrence evidence to the result saved in the database.

    The data is stored inside harm_breakdown and the best detection,
    so a new database column is not required.
    """

    result.setdefault("harm_breakdown", {})

    recurrence_breakdown = result[
        "harm_breakdown"
    ].setdefault(
        "recurrence",
        {},
    )

    recurrence_breakdown.update(
        recurrence_details
    )

    if result.get("detections"):
        best_detection = max(
            result["detections"],
            key=lambda item: item["confidence"],
        )

        best_detection["recurrence"] = (
            recurrence_details
        )

    if "similarity-v1" not in result["model_version"]:
        result["model_version"] += (
            "+similarity-v1"
        )

    return result


def classify_report_in_background(
    report_id: int,
) -> None:
    """Automatically classify and save one report."""

    db = SessionLocal()

    try:
        report = (
            db.query(Report)
            .filter(Report.id == report_id)
            .first()
        )

        if not report:
            print(
                "Automatic classification skipped: "
                f"report #{report_id} was not found."
            )
            return

        if not report.image_url:
            print(
                "Automatic classification skipped: "
                f"report #{report_id} has no image."
            )
            return

        print(
            "Starting automatic classification "
            f"for report #{report_id}..."
        )

        # First confirm whether the current image contains graffiti.
        # The final harm score is recalculated after recurrence and
        # location checks are completed.
        result = classification_service.classify_image(
            image_url=report.image_url,
            occurrence_count=1,
        )

        if result["graffiti_detected"]:
            recurrence_details = (
                calculate_recurrence_details(
                    db,
                    report,
                )
            )
        else:
            recurrence_details = (
                empty_recurrence_details()
            )

        occurrence_count = recurrence_details[
            "occurrence_count"
        ]

        print(
            f"Recurrence check for report #{report_id}: "
            f"occurrence #{occurrence_count}, "
            f"similar nearby reports: "
            f"{recurrence_details['similar_report_count']}, "
            f"radius: "
            f"{RECURRENCE_RADIUS_METRES:.0f} metres, "
            f"time window: "
            f"{RECURRENCE_WINDOW_DAYS} days."
        )

        result = add_location_result(
            result=result,
            latitude=report.latitude,
            longitude=report.longitude,
            occurrence_count=occurrence_count,
        )

        result = add_recurrence_result(
            result=result,
            recurrence_details=recurrence_details,
        )

        classification = Classification(
            report_id=report.id,
            graffiti_detected=result[
                "graffiti_detected"
            ],
            surface_type=result["surface_type"],
            tag_category=result["tag_category"],
            location_type=result["location_type"],
            size_category=result["size_category"],
            ai_surface_type=result["surface_type"],
            ai_tag_category=result["tag_category"],
            ai_location_type=result["location_type"],
            ai_size_category=result["size_category"],
            detection_confidence=result[
                "detection_confidence"
            ],
            manual_review_required=result[
                "manual_review_required"
            ],
            manually_reviewed=False,
            detections=result["detections"],
            harm_score=result["harm_score"],
            severity_band=result["severity_band"],
            harm_breakdown=result["harm_breakdown"],
            model_version=result["model_version"],
        )

        db.add(classification)
        db.commit()
        db.refresh(classification)

        print(
            "Automatic classification completed for "
            f"report #{report_id}. "
            f"Classification ID: {classification.id}, "
            f"occurrence: {occurrence_count}, "
            f"similar reports: "
            f"{recurrence_details['similar_report_count']}, "
            f"location: {classification.location_type}, "
            f"harm score: {classification.harm_score}, "
            f"severity: {classification.severity_band}."
        )

    except Exception as error:
        db.rollback()

        print(
            "Automatic classification failed for "
            f"report #{report_id}: {error}"
        )

    finally:
        db.close()
