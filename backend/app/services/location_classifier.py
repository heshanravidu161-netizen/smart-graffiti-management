"""
Automatic location-visibility classification.

The report's GPS coordinates are checked against OpenStreetMap.
The returned map feature is converted into one of the location
categories used by the harm-scoring framework.
"""

import requests


NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org/reverse"
)

REQUEST_TIMEOUT_SECONDS = 15

LOCATION_REVIEW_THRESHOLD = 0.70


MAIN_STREET_TYPES = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
}

SIDE_STREET_TYPES = {
    "tertiary",
    "residential",
    "unclassified",
    "living_street",
}

LANEWAY_TYPES = {
    "service",
    "pedestrian",
    "footway",
    "path",
    "track",
}

SCHOOL_TYPES = {
    "school",
    "kindergarten",
    "college",
    "university",
}

TRANSPORT_TYPES = {
    "station",
    "bus_station",
    "bus_stop",
    "platform",
    "tram_stop",
    "halt",
}


def unknown_location(
    reason: str,
) -> dict:
    """Return a safe fallback when map data is unavailable."""

    return {
        "location_type": "unknown",
        "confidence": 0.0,
        "accepted_for_scoring": False,
        "map_category": None,
        "map_type": None,
        "display_name": None,
        "reason": reason,
        "source": "openstreetmap-nominatim",
        "version": "location-osm-v1",
    }


def classify_location(
    latitude: float,
    longitude: float,
) -> dict:
    """
    Classify location visibility using GPS and OpenStreetMap.

    This function safely returns unknown when map information
    is missing or the external request fails.
    """

    if not (-90 <= latitude <= 90):
        return unknown_location(
            "Latitude is outside the valid range."
        )

    if not (-180 <= longitude <= 180):
        return unknown_location(
            "Longitude is outside the valid range."
        )

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
                "extratags": 1,
                "zoom": 18,
            },
            headers={
                "User-Agent": (
                    "UrbanEyes-Student-Project/1.0"
                ),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
        map_data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as error:
        return unknown_location(
            f"Map request failed: {error}"
        )

    map_category = str(
        map_data.get("category", "")
    ).lower()

    map_type = str(
        map_data.get("type", "")
    ).lower()

    display_name = map_data.get(
        "display_name"
    )

    location_type = "unknown"
    confidence = 0.0
    reason = "The map feature could not be classified."

    if (
        map_category == "amenity"
        and map_type in SCHOOL_TYPES
    ):
        location_type = "school_zone"
        confidence = 0.90
        reason = "The coordinates identify an educational facility."

    elif (
        map_category in {
            "railway",
            "public_transport",
        }
        or map_type in TRANSPORT_TYPES
    ):
        location_type = "transport_hub"
        confidence = 0.90
        reason = "The coordinates identify a transport facility."

    elif (
        map_category == "highway"
        and map_type in MAIN_STREET_TYPES
    ):
        location_type = "main_street"
        confidence = 0.85
        reason = "The coordinates identify a major road."

    elif (
        map_category == "highway"
        and map_type in SIDE_STREET_TYPES
    ):
        location_type = "side_street"
        confidence = 0.80
        reason = "The coordinates identify a local road."

    elif (
        map_category == "highway"
        and map_type in LANEWAY_TYPES
    ):
        location_type = "laneway"
        confidence = 0.75
        reason = "The coordinates identify a service lane or path."

    accepted = (
        confidence >= LOCATION_REVIEW_THRESHOLD
        and location_type != "unknown"
    )

    return {
        "location_type": location_type,
        "confidence": round(confidence, 3),
        "accepted_for_scoring": accepted,
        "map_category": map_category or None,
        "map_type": map_type or None,
        "display_name": display_name,
        "reason": reason,
        "source": "openstreetmap-nominatim",
        "version": "location-osm-v1",
    }
