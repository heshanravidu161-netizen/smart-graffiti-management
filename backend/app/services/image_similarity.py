"""
Visual similarity checking for graffiti reports.

Two reports are treated as visually similar when their images have
a sufficiently similar perceptual hash or enough matching OpenCV
features. This is used together with GPS distance for recurrence.
"""

from functools import lru_cache

import cv2
import numpy as np
import requests


REQUEST_TIMEOUT_SECONDS = 20
MAXIMUM_IMAGE_SIZE = 20 * 1024 * 1024

HASH_SIMILARITY_THRESHOLD = 0.88
MINIMUM_GOOD_MATCHES = 15
ORB_SIMILARITY_THRESHOLD = 0.08


@lru_cache(maxsize=8)
def download_image(image_url: str) -> np.ndarray:
    """Download and decode an image as an OpenCV array."""

    response = requests.get(
        image_url,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    if len(response.content) > MAXIMUM_IMAGE_SIZE:
        raise ValueError(
            "The comparison image exceeds 20 MB."
        )

    image_array = np.frombuffer(
        response.content,
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "The downloaded file could not be decoded as an image."
        )

    return image


def prepare_grayscale(
    image: np.ndarray,
) -> np.ndarray:
    """Convert an image to grayscale and limit its dimensions."""

    height, width = image.shape[:2]
    maximum_dimension = 1000

    if max(height, width) > maximum_dimension:
        scale = maximum_dimension / max(
            height,
            width,
        )

        image = cv2.resize(
            image,
            (
                int(width * scale),
                int(height * scale),
            ),
            interpolation=cv2.INTER_AREA,
        )

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )


def difference_hash(
    grayscale_image: np.ndarray,
) -> np.ndarray:
    """Create a 64-bit perceptual difference hash."""

    resized = cv2.resize(
        grayscale_image,
        (9, 8),
        interpolation=cv2.INTER_AREA,
    )

    return resized[:, 1:] > resized[:, :-1]


def hash_similarity(
    image_1: np.ndarray,
    image_2: np.ndarray,
) -> float:
    """Return perceptual-hash similarity from 0 to 1."""

    hash_1 = difference_hash(image_1)
    hash_2 = difference_hash(image_2)

    different_bits = np.count_nonzero(
        hash_1 != hash_2
    )

    return 1.0 - (
        different_bits / hash_1.size
    )


def orb_similarity(
    image_1: np.ndarray,
    image_2: np.ndarray,
) -> tuple[int, float]:
    """Compare local image features using OpenCV ORB."""

    detector = cv2.ORB_create(
        nfeatures=1500,
    )

    keypoints_1, descriptors_1 = (
        detector.detectAndCompute(
            image_1,
            None,
        )
    )

    keypoints_2, descriptors_2 = (
        detector.detectAndCompute(
            image_2,
            None,
        )
    )

    if (
        descriptors_1 is None
        or descriptors_2 is None
        or not keypoints_1
        or not keypoints_2
    ):
        return 0, 0.0

    matcher = cv2.BFMatcher(
        cv2.NORM_HAMMING,
        crossCheck=False,
    )

    possible_matches = matcher.knnMatch(
        descriptors_1,
        descriptors_2,
        k=2,
    )

    good_matches = []

    for match_pair in possible_matches:
        if len(match_pair) < 2:
            continue

        closest_match, second_match = match_pair

        if closest_match.distance < 0.75 * second_match.distance:
            good_matches.append(
                closest_match
            )

    comparison_base = min(
        len(keypoints_1),
        len(keypoints_2),
    )

    similarity = (
        len(good_matches) / comparison_base
        if comparison_base > 0
        else 0.0
    )

    return len(good_matches), similarity


def compare_images(
    image_url_1: str,
    image_url_2: str,
) -> dict:
    """
    Compare two report images.

    A positive result is still an experimental similarity
    recommendation rather than guaranteed identity.
    """

    try:
        image_1 = prepare_grayscale(
            download_image(image_url_1)
        )

        image_2 = prepare_grayscale(
            download_image(image_url_2)
        )

        perceptual_similarity = hash_similarity(
            image_1,
            image_2,
        )

        good_matches, feature_similarity = (
            orb_similarity(
                image_1,
                image_2,
            )
        )

        hash_match = (
            perceptual_similarity
            >= HASH_SIMILARITY_THRESHOLD
        )

        feature_match = (
            good_matches >= MINIMUM_GOOD_MATCHES
            and feature_similarity
            >= ORB_SIMILARITY_THRESHOLD
        )

        visually_similar = (
            hash_match or feature_match
        )

        return {
            "visually_similar": bool(visually_similar),
            "hash_similarity": float(
                round(perceptual_similarity, 3)
            ),
            "good_feature_matches": good_matches,
            "feature_similarity": float(
                round(feature_similarity, 3)
            ),
            "reason": (
                "Images passed the visual similarity check."
                if visually_similar
                else "Images did not pass the similarity thresholds."
            ),
            "version": "similarity-v1",
        }

    except Exception as error:
        return {
            "visually_similar": False,
            "hash_similarity": 0.0,
            "good_feature_matches": 0,
            "feature_similarity": 0.0,
            "reason": (
                f"Image comparison failed: {error}"
            ),
            "version": "similarity-v1",
        }
