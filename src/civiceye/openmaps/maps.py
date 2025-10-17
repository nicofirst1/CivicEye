from typing import Dict, Optional

import requests
import streamlit as st

MAP_ZOOM = 17
MAP_SIZE = "400x400"
OSM_TILE_SERVER = "https://staticmap.openstreetmap.de/staticmap.php"
DEFAULT_HEADERS = {
    "User-Agent": "CivicEye/1.0 (+https://github.com/USERNAME/REPOSITORY)"
}


def build_map_url(lat: float, lon: float) -> Dict[str, str]:
    """Return a URL and provider label for the static map image."""
    url = (
        f"{OSM_TILE_SERVER}?center={lat},{lon}&zoom={MAP_ZOOM}&size={MAP_SIZE}"
        f"&markers={lat},{lon},red-pushpin"
    )
    return {"url": url, "provider": "OpenStreetMap Static Map"}


@st.cache_data(show_spinner=False)
def fetch_map_image(map_url: str) -> Optional[bytes]:
    """Download the static map image so we can display it and compute embeddings."""
    try:
        response = requests.get(map_url, timeout=30, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None
