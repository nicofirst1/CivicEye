import logging
from typing import Dict, List, Optional

import requests
import streamlit as st

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

REQUEST_HEADERS = {
    "User-Agent": "CivicEye/1.0 (+https://github.com/USERNAME/REPOSITORY)",
}

logger = logging.getLogger(__name__)


def build_overpass_query(zip_code: str, house_number: str) -> str:
    """Build an Overpass API query matching housenumber and postcode."""
    return f"""
    [out:json][timeout:30];
    (
      node["addr:postcode"="{zip_code}"]["addr:housenumber"="{house_number}"];
      way["addr:postcode"="{zip_code}"]["addr:housenumber"="{house_number}"];
      relation["addr:postcode"="{zip_code}"]["addr:housenumber"="{house_number}"];
    );
    out center tags;
    """


@st.cache_data(ttl=600, show_spinner=False)
def fetch_addresses(zip_code: str, house_number: str) -> List[Dict[str, object]]:
    """Query Overpass API for all addresses matching the ZIP and house number."""
    query = build_overpass_query(zip_code, house_number)

    last_error: Optional[requests.RequestException] = None
    for endpoint in OVERPASS_ENDPOINTS:
        logger.debug("Querying Overpass endpoint %s", endpoint)
        try:
            response = requests.get(
                endpoint,
                params={"data": query},
                timeout=45,
                headers=REQUEST_HEADERS,
            )
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Overpass endpoint %s failed: %s", endpoint, exc)
            continue

        if response.status_code == 429:
            last_error = requests.RequestException(
                "Overpass API rate limit hit. Please try again later."
            )
            continue

        if response.status_code >= 500:
            last_error = requests.RequestException(
                f"Overpass API server error ({response.status_code})."
            )
            logger.warning("Overpass endpoint %s returned %s", endpoint, response.status_code)
            continue

        if response.status_code >= 400:
            last_error = requests.RequestException(
                f"Overpass API returned HTTP {response.status_code}."
            )
            logger.warning("Overpass endpoint %s returned %s", endpoint, response.status_code)
            continue

        try:
            payload = response.json()
        except ValueError as exc:
            last_error = requests.RequestException(
                "Overpass API returned invalid JSON payload."
            )
            logger.warning("Overpass endpoint %s returned invalid JSON: %s", endpoint, exc)
            continue

        elements = payload.get("elements", [])
        return _extract_matches(elements)

    raise requests.RequestException(
        "All Overpass API endpoints failed. "
        "Please retry in a few minutes or check your network connection."
    ) from last_error


def _extract_matches(elements: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Normalize Overpass response elements into address dictionaries."""
    matches: List[Dict[str, object]] = []
    for element in elements:
        center = element.get("center", {})
        tags = element.get("tags", {})
        lat = element.get("lat") or center.get("lat")
        lon = element.get("lon") or center.get("lon")

        if lat is None or lon is None:
            continue

        matches.append(
            {
                "street": tags.get("addr:street", "Unknown street"),
                "city": tags.get("addr:city"),
                "lat": float(lat),
                "lon": float(lon),
            }
        )
    return matches
