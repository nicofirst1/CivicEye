from typing import Dict, List

import requests
import streamlit as st


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
    response = requests.get(
        "https://overpass-api.de/api/interpreter",
        params={"data": query},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    elements = payload.get("elements", [])

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
