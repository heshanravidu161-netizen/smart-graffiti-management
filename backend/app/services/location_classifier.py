"""
Automatic location-visibility classification.

The report's GPS coordinates are checked against OpenStreetMap.
The returned map feature is converted into one of the location
categories used by the harm-scoring framework.

If the exact location returns an unclear feature such as
building=yes, the classifier performs a wider street-level lookup.

Based on Dr.Davids feedback location is used to identify high risk areas such as heritage sites
"""

import time

import requests


NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org/reverse"
)

REQUEST_TIMEOUT_SECONDS = 15

LOCATION_REVIEW_THRESHOLD = 0.70

# Zoom 18 normally returns a building or exact feature.
# Zoom 17 and 16 provide street-level fallback information.
LOCATION_ZOOM_LEVELS = (
    18,
    17,
    16,
)

# Avoid sending requests too quickly to the public
# OpenStreetMap Nominatim service.
FALLBACK_REQUEST_DELAY_SECONDS = 1.1


MAIN_STREET_TYPES = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
}

SIDE_STREET_TYPES = {
    "tertiary",
    "tertiary_link",
    "residential",
    "unclassified",
    "living_street",
    "road",
}

LANEWAY_TYPES = {
    "service",
    "pedestrian",
    "footway",
    "path",
    "track",
    "cycleway",
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

# OpenStreetMap feature types that normally identify a heritage,
# protected or historically significant place.
HERITAGE_CATEGORIES = {
    "historic",
}

HERITAGE_TYPES = {
    "archaeological_site",
    "battlefield",
    "castle",
    "fort",
    "heritage",
    "manor",
    "memorial",
    "monument",
    "ruins",
    "wayside_cross",
    "wayside_shrine",
}

# Important public buildings and facilities receive the same high
# location score as schools, transport hubs and main streets.
IMPORTANT_AMENITY_TYPES = {
    "arts_centre",
    "clinic",
    "community_centre",
    "courthouse",
    "fire_station",
    "hospital",
    "library",
    "place_of_worship",
    "police",
    "public_building",
    "social_facility",
    "townhall",
}

IMPORTANT_OFFICE_TYPES = {
    "government",
}

IMPORTANT_TOURISM_TYPES = {
    "gallery",
    "museum",
}

PROTECTED_TYPES = {
    "national_park",
    "protected_area",
}


def get_extra_tags(
    map_data: dict,
) -> dict:
    """Return lower-case OpenStreetMap extra tags safely."""

    raw_extra_tags = map_data.get("extratags")

    if not isinstance(raw_extra_tags, dict):
        return {}

    return {
        str(key).lower(): str(value).lower()
        for key, value in raw_extra_tags.items()
        if value is not None
    }


def identify_significant_site(
    map_data: dict,
) -> tuple[str, str] | None:
    """
    Identify a heritage/protected site or important public building.

    The returned tuple contains the significance type and a readable
    explanation. None means that no reliable significance tag exists.
    """

    map_category = str(
        map_data.get("category", "")
    ).lower()

    map_type = str(
        map_data.get("type", "")
    ).lower()

    extra_tags = get_extra_tags(map_data)

    has_heritage_tag = any(
        extra_tags.get(key, "")
        not in {"", "no", "false", "0"}
        for key in (
            "heritage",
            "heritage:operator",
            "historic",
            "ref:heritage",
            "ref:wa_heritage",
        )
    )

    has_protection_tag = any(
        extra_tags.get(key, "")
        not in {"", "no", "false", "0"}
        for key in (
            "protect_class",
            "protection_title",
        )
    )

    if (
        map_category in HERITAGE_CATEGORIES
        or map_type in HERITAGE_TYPES
        or has_heritage_tag
    ):
        return (
            "heritage_site",
            "OpenStreetMap identifies this location as a heritage "
            "or historically significant site.",
        )

    if (
        map_type in PROTECTED_TYPES
        or has_protection_tag
        or (
            map_category == "boundary"
            and map_type == "protected_area"
        )
    ):
        return (
            "protected_site",
            "OpenStreetMap identifies this location as a protected "
            "or nationally significant place.",
        )

    if (
        (
            map_category == "amenity"
            and map_type in IMPORTANT_AMENITY_TYPES
        )
        or (
            map_category == "office"
            and map_type in IMPORTANT_OFFICE_TYPES
        )
        or (
            map_category == "tourism"
            and map_type in IMPORTANT_TOURISM_TYPES
        )
    ):
        return (
            "important_public_building",
            "OpenStreetMap identifies this location as an important "
            "public or community building.",
        )

    return None


def unknown_location(
    reason: str,
    map_data: dict | None = None,
    lookup_zoom: int | None = None,
    fallback_used: bool = False,
) -> dict:
    """Return a safe fallback when map data is unavailable."""

    map_data = map_data or {}

    map_category = str(
        map_data.get("category", "")
    ).lower()

    map_type = str(
        map_data.get("type", "")
    ).lower()

    return {
        "location_type": "unknown",
        "confidence": 0.0,
        "accepted_for_scoring": False,
        "map_category": map_category or None,
        "map_type": map_type or None,
        "display_name": map_data.get(
            "display_name"
        ),
        "reason": reason,
        "source": "openstreetmap-nominatim",
        "version": "location-osm-v2",
        "lookup_zoom": lookup_zoom,
        "fallback_used": fallback_used,
        "significant_site_detected": False,
        "significance_type": None,
    }


def request_map_data(
    latitude: float,
    longitude: float,
    zoom: int,
) -> dict:
    """Request one reverse-geocoding result from Nominatim."""

    response = requests.get(
        NOMINATIM_URL,
        params={
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "zoom": zoom,
        },
        headers={
            "User-Agent": (
                "UrbanEyes-Student-Project/2.0"
            ),
            "Accept-Language": "en",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    map_data = response.json()

    if not isinstance(map_data, dict):
        raise ValueError(
            "The map service returned an invalid response."
        )

    return map_data


def classify_map_feature(
    map_data: dict,
    lookup_zoom: int,
    fallback_used: bool,
) -> dict | None:
    """
    Convert one OpenStreetMap feature into a scoring category.

    None is returned when the feature cannot be classified, allowing
    classify_location() to perform a wider fallback lookup.
    """

    map_category = str(
        map_data.get("category", "")
    ).lower()

    map_type = str(
        map_data.get("type", "")
    ).lower()

    display_name = map_data.get(
        "display_name"
    )

    location_type = None
    confidence = 0.0
    reason = None
    significance_type = None

    significant_site = identify_significant_site(
        map_data
    )

    if significant_site is not None:
        significance_type, reason = significant_site
        location_type = "heritage_or_important_site"
        confidence = 0.95

    elif (
        map_category == "amenity"
        and map_type in SCHOOL_TYPES
    ):
        location_type = "school_zone"
        confidence = 0.90
        reason = (
            "The coordinates identify an "
            "educational facility."
        )

    elif (
        map_category in {
            "railway",
            "public_transport",
        }
        or map_type in TRANSPORT_TYPES
    ):
        location_type = "transport_hub"
        confidence = 0.90
        reason = (
            "The coordinates identify a "
            "transport facility."
        )

    elif (
        map_category == "highway"
        and map_type in MAIN_STREET_TYPES
    ):
        location_type = "main_street"
        confidence = 0.85
        reason = (
            "The coordinates identify a major road."
        )

    elif (
        map_category == "highway"
        and map_type in SIDE_STREET_TYPES
    ):
        location_type = "side_street"
        confidence = 0.80
        reason = (
            "The coordinates identify a local road."
        )

    elif (
        map_category == "highway"
        and map_type in LANEWAY_TYPES
    ):
        location_type = "laneway"
        confidence = 0.75
        reason = (
            "The coordinates identify a "
            "service lane or path."
        )

    if location_type is None:
        return None

    if fallback_used:
        reason = (
            f"{reason} A street-level fallback lookup "
            "was used because the exact map feature "
            "was unclear."
        )

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
        "version": "location-osm-v2",
        "lookup_zoom": lookup_zoom,
        "fallback_used": fallback_used,
        "significant_site_detected": (
            significance_type is not None
        ),
        "significance_type": significance_type,
    }


def classify_location(
    latitude: float,
    longitude: float,
) -> dict:
    """
    Classify location visibility using GPS and OpenStreetMap.

    The exact feature is checked first. If it cannot be classified,
    wider street-level lookups are attempted.

    The function safely returns unknown when reliable map
    information cannot be obtained.
    """

    if not (-90 <= latitude <= 90):
        return unknown_location(
            "Latitude is outside the valid range."
        )

    if not (-180 <= longitude <= 180):
        return unknown_location(
            "Longitude is outside the valid range."
        )

    first_map_data = None
    last_map_data = None
    last_zoom = None

    for index, zoom in enumerate(
        LOCATION_ZOOM_LEVELS
    ):
        fallback_used = index > 0

        if fallback_used:
            time.sleep(
                FALLBACK_REQUEST_DELAY_SECONDS
            )

        try:
            map_data = request_map_data(
                latitude=latitude,
                longitude=longitude,
                zoom=zoom,
            )

        except (
            requests.RequestException,
            ValueError,
        ) as error:
            return unknown_location(
                reason=f"Map request failed: {error}",
                map_data=first_map_data,
                lookup_zoom=last_zoom,
                fallback_used=fallback_used,
            )

        if first_map_data is None:
            first_map_data = map_data

        last_map_data = map_data
        last_zoom = zoom

        result = classify_map_feature(
            map_data=map_data,
            lookup_zoom=zoom,
            fallback_used=fallback_used,
        )

        if result is not None:
            # Preserve the more detailed address from the exact
            # lookup while using the fallback feature for the
            # location classification.
            if (
                fallback_used
                and first_map_data is not None
                and first_map_data.get("display_name")
            ):
                result["display_name"] = (
                    first_map_data["display_name"]
                )

            return result

    return unknown_location(
        reason=(
            "The exact map feature and nearby "
            "street-level features could not be "
            "matched to a scoring category."
        ),
        map_data=first_map_data or last_map_data,
        lookup_zoom=last_zoom,
        fallback_used=True,
    )
