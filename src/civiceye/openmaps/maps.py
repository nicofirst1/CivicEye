import logging
import os
from pathlib import Path
from typing import Dict, Optional

import requests
import streamlit as st

MAP_ZOOM = 17
MAP_SIZE = "400x400"
GOOGLE_STATIC_BASE = "https://maps.googleapis.com/maps/api/staticmap"
GOOGLE_STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"
GOOGLE_METADATA_BASE = "https://maps.googleapis.com/maps/api/streetview/metadata"
LOCAL_KEY_PATH = Path(".streamlit/google_maps_api_key.txt")

DEFAULT_HEADERS = {
    "User-Agent": "CivicEye/1.0 (+https://github.com/USERNAME/REPOSITORY)",
}

logger = logging.getLogger(__name__)


def get_google_maps_api_key() -> Optional[str]:
    """Load the Google Maps API key from env vars or the local file."""
    env_value = os.getenv("GOOGLE_MAPS_API_KEY")
    if env_value:
        return env_value.strip()

    if LOCAL_KEY_PATH.exists():
        try:
            return LOCAL_KEY_PATH.read_text(encoding="utf-8").strip()
        except OSError as exc:  # pragma: no cover - unexpected IO errors
            logger.warning("Failed to read stored Google Maps API key: %s", exc)
    return None


def save_google_maps_api_key(api_key: str) -> None:
    """Persist the Google Maps API key so Streamlit sessions can reuse it."""
    api_key = api_key.strip()
    LOCAL_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_KEY_PATH.write_text(api_key, encoding="utf-8")


def _fetch_street_view_metadata(lat: float, lon: float, api_key: str) -> Dict[str, object]:
    """Call the Street View metadata endpoint to determine availability and POV."""
    params = {
        "location": f"{lat},{lon}",
        "key": api_key,
    }
    try:
        response = requests.get(GOOGLE_METADATA_BASE, params=params, timeout=15, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.warning("Street View metadata request failed: %s", exc)
        return {"status": "ERROR", "error_message": str(exc)}


def _build_street_view_url(lat: float, lon: float, api_key: str, heading: Optional[float]) -> str:
    """Construct a Street View static image URL for the given point of view."""
    url = (
        f"{GOOGLE_STREET_VIEW_BASE}?size={MAP_SIZE}&location={lat},{lon}"
        f"&pitch=0&fov=90&key={api_key}"
    )
    if heading is not None:
        url += f"&heading={heading}"
    return url


def _fetch_google_street_view(lat: float, lon: float, api_key: str) -> Dict[str, Optional[object]]:
    """Attempt to retrieve a Google Street View image for the target location."""
    metadata = _fetch_street_view_metadata(lat, lon, api_key)
    status = metadata.get("status", "UNKNOWN")

    if status != "OK":
        message = metadata.get("error_message") or "Street View imagery unavailable for this location."
        if status == "ZERO_RESULTS":
            message = "Street View imagery unavailable for this location."
        logger.info("Street View metadata status %s for %s,%s: %s", status, lat, lon, message)
        return {"image": None, "url": None, "error": message}

    heading = None
    pov = metadata.get("pov")
    if isinstance(pov, dict):
        heading = pov.get("heading")

    street_view_url = _build_street_view_url(lat, lon, api_key, heading)
    try:
        response = requests.get(street_view_url, timeout=30, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image"):
            logger.warning("Street View content type unexpected: %s", content_type)
            return {"image": None, "url": street_view_url, "error": "Invalid Street View response."}

        error_header = response.headers.get("X-Static-Street-View-Error-Code")
        if error_header:
            logger.info("Street View error header for %s,%s: %s", lat, lon, error_header)
            return {"image": None, "url": street_view_url, "error": "Street View imagery unavailable."}

        viewer_url = (
            "https://www.google.com/maps/@?"
            f"api=1&map_action=pano&viewpoint={lat},{lon}"
            + (f"&heading={heading}" if heading is not None else "")
        )
        return {"image": response.content, "url": viewer_url, "error": None}
    except requests.RequestException as exc:
        logger.warning("Failed to fetch Google Street View image: %s", exc)
        return {"image": None, "url": street_view_url, "error": str(exc)}


def _build_google_static_url(lat: float, lon: float, api_key: str) -> str:
    """Construct a static map URL centered on the given coordinates."""
    return (
        f"{GOOGLE_STATIC_BASE}?center={lat},{lon}&zoom={MAP_ZOOM}&size={MAP_SIZE}"
        f"&markers=color:red%7C{lat},{lon}&key={api_key}"
    )


def _fetch_google_static_map(lat: float, lon: float, api_key: str) -> Dict[str, Optional[object]]:
    """Download a Google static map image."""
    map_url = _build_google_static_url(lat, lon, api_key)
    try:
        response = requests.get(map_url, timeout=30, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image"):
            logger.warning("Unexpected content type from Google Static Maps: %s", content_type)
            return {"image": None, "url": map_url, "error": "Invalid response from Google Maps."}
        return {"image": response.content, "url": map_url, "error": None}
    except requests.RequestException as exc:
        logger.warning("Failed to fetch Google static map: %s", exc)
        return {"image": None, "url": map_url, "error": str(exc)}


@st.cache_data(show_spinner=False)
def fetch_map_image_for_location(lat: float, lon: float) -> Dict[str, Optional[object]]:
    """Return imagery for the requested location, preferring Street View."""
    api_key = get_google_maps_api_key()
    if not api_key:
        return {
            "image": None,
            "provider": "Google Street View API (missing key)",
            "url": f"https://www.google.com/maps?q={lat},{lon}",
            "error": "Google Maps API key not configured.",
        }

    street_view = _fetch_google_street_view(lat, lon, api_key)
    if street_view["image"]:
        return {
            "image": street_view["image"],
            "provider": "Google Street View API",
            "url": street_view["url"],
            "error": None,
        }

    static_map = _fetch_google_static_map(lat, lon, api_key)
    provider = "Google Maps Static API"
    error = static_map["error"]
    if street_view["error"] and not error:
        error = street_view["error"]
    return {
        "image": static_map["image"],
        "provider": provider,
        "url": static_map["url"],
        "error": error,
    }
