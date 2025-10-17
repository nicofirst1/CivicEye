from typing import List

import requests
import streamlit as st

from ..clip.similarity import compute_similarity_scores
from ..openmaps.maps import build_map_url, fetch_map_image
from ..openmaps.models import AddressCandidate
from ..openmaps.overpass import fetch_addresses

SESSION_RESULTS_KEY = "civiceye_results"
SESSION_SELECTED_ID_KEY = "civiceye_selected_id"
SESSION_HAS_SIMILARITY_KEY = "civiceye_has_similarity"


def configure_page() -> None:
    """Configure the Streamlit page."""
    st.set_page_config(page_title="CivicEye", layout="wide")
    st.title("CivicEye")
    st.caption("Find and compare all street level matches for a given civic number within a German ZIP code.")


def handle_search(zip_code: str, house_number: str, uploaded_image) -> None:
    """Execute the search flow: Overpass query, map generation, optional similarity."""
    st.session_state.pop(SESSION_RESULTS_KEY, None)
    st.session_state.pop(SESSION_SELECTED_ID_KEY, None)
    st.session_state.pop(SESSION_HAS_SIMILARITY_KEY, None)

    try:
        with st.spinner("Contacting OpenStreetMap…"):
            address_rows = fetch_addresses(zip_code, house_number)
    except requests.RequestException as exc:
        st.error(f"Failed to query Overpass API: {exc}")
        return

    if not address_rows:
        st.warning("No addresses found for that ZIP code and house number combination.")
        return

    candidates: List[AddressCandidate] = []
    for index, row in enumerate(address_rows):
        map_meta = build_map_url(row["lat"], row["lon"])
        map_bytes = fetch_map_image(map_meta["url"])

        candidate = AddressCandidate(
            id=f"{row['lat']:.6f}|{row['lon']:.6f}|{index}",
            street=str(row["street"]),
            city=str(row["city"]) if row.get("city") else None,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            map_url=map_meta["url"],
            map_provider=map_meta["provider"],
            map_image=map_bytes,
        )
        candidates.append(candidate)

    if uploaded_image:
        st.info("Computing similarity scores against the uploaded image…")
        candidates = compute_similarity_scores(uploaded_image, candidates)
        has_similarity = True
    else:
        has_similarity = False

    st.session_state[SESSION_RESULTS_KEY] = candidates
    st.session_state[SESSION_HAS_SIMILARITY_KEY] = has_similarity


def render_card_grid(candidates: List[AddressCandidate], selected_id: str) -> None:
    """Render the map cards in a responsive grid."""
    if not candidates:
        return

    cols_per_row = 3
    for start in range(0, len(candidates), cols_per_row):
        row_candidates = candidates[start : start + cols_per_row]
        columns = st.columns(len(row_candidates))
        for column, candidate in zip(columns, row_candidates):
            with column:
                if candidate.map_image:
                    st.image(candidate.map_image, use_column_width=True)
                else:
                    st.image(candidate.map_url, use_column_width=True)

                street_line = candidate.street
                if candidate.city:
                    street_line += f", {candidate.city}"

                st.write(street_line)
                st.caption(f"{candidate.lat:.5f}, {candidate.lon:.5f}")

                if candidate.similarity is not None:
                    st.metric("Similarity", f"{candidate.similarity:.2f}")

                if candidate.id == selected_id:
                    st.success("Selected")
                else:
                    st.button(
                        "Select",
                        key=f"select_btn_{candidate.id}",
                        on_click=lambda cid=candidate.id: st.session_state.update(
                            {SESSION_SELECTED_ID_KEY: cid}
                        ),
                    )


def display_results() -> None:
    """Display search results, selection controls, and the selected detail view."""
    candidates: List[AddressCandidate] = st.session_state.get(SESSION_RESULTS_KEY, [])
    if not candidates:
        return

    has_similarity = st.session_state.get(SESSION_HAS_SIMILARITY_KEY, False)

    st.subheader(f"Found {len(candidates)} possible addresses.")
    if has_similarity:
        st.caption("Sorted by cosine similarity against your uploaded reference image.")

    option_labels = {
        candidate.id: f"{candidate.street}"
        + (f", {candidate.city}" if candidate.city else "")
        for candidate in candidates
    }

    option_ids = list(option_labels.keys())
    default_id = st.session_state.get(SESSION_SELECTED_ID_KEY, option_ids[0])
    default_index = option_ids.index(default_id) if default_id in option_ids else 0

    selected_id = st.radio(
        "Select an address",
        options=option_ids,
        index=default_index,
        format_func=lambda cid: option_labels.get(cid, cid),
        key=SESSION_SELECTED_ID_KEY,
    )

    render_card_grid(candidates, selected_id)

    selected_candidate = next(
        candidate for candidate in candidates if candidate.id == selected_id
    )

    st.divider()
    st.subheader("Selected address")
    st.write(
        f"{selected_candidate.street}"
        + (f", {selected_candidate.city}" if selected_candidate.city else "")
    )
    st.write(f"Coordinates: {selected_candidate.lat:.6f}, {selected_candidate.lon:.6f}")
    st.caption(f"Map provider: {selected_candidate.map_provider}")

    if selected_candidate.map_image:
        st.image(selected_candidate.map_image, caption="Preview", use_column_width=True)
    else:
        st.image(selected_candidate.map_url, caption="Preview", use_column_width=True)

    maps_link = f"https://www.google.com/maps?q={selected_candidate.lat},{selected_candidate.lon}"
    st.link_button("Open in Google Maps", maps_link)


def render_search_form() -> None:
    """Render the user input form."""
    st.caption("Map previews are generated with OpenStreetMap static tiles (no API key required).")
    with st.form("search_form"):
        zip_code = st.text_input("ZIP code (5 digits)", max_chars=5)
        house_number = st.text_input("House number", max_chars=10)
        uploaded_image = st.file_uploader(
            "Optional: upload a reference photo (JPG or PNG)", type=["png", "jpg", "jpeg"]
        )
        submitted = st.form_submit_button("Search Addresses")

    if submitted:
        if not zip_code or not house_number:
            st.error("Please provide both a ZIP code and a house number.")
            return
        if len(zip_code.strip()) != 5 or not zip_code.strip().isdigit():
            st.error("ZIP code must be a 5-digit string.")
            return

        handle_search(zip_code.strip(), house_number.strip(), uploaded_image)


def main() -> None:
    """Entrypoint used by Streamlit."""
    configure_page()
    render_search_form()
    display_results()
