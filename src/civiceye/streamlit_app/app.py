from typing import List, Optional

import requests
import streamlit as st

from ..clip.similarity import compute_similarity_scores
from ..openmaps.maps import (
    fetch_map_image_for_location,
    get_google_maps_api_key,
    save_google_maps_api_key,
)
from ..openmaps.models import AddressCandidate
from ..openmaps.overpass import fetch_addresses

SESSION_RESULTS_KEY = "civiceye_results"
SESSION_SELECTED_ID_KEY = "civiceye_selected_id"
SESSION_HAS_SIMILARITY_KEY = "civiceye_has_similarity"
SESSION_API_KEY_SAVED_FLAG = "civiceye_api_key_saved"
SESSION_CAROUSEL_INDEX_KEY = "civiceye_carousel_index"


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
    st.session_state[SESSION_CAROUSEL_INDEX_KEY] = 0

    try:
        with st.spinner("Contacting OpenStreetMap…"):
            address_rows = fetch_addresses(zip_code, house_number)
    except requests.RequestException as exc:
        st.error(f"Failed to query Overpass API: {exc}")
        st.info(
            "The Overpass API occasionally times out under heavy load. "
            "Wait a minute and press **Search Addresses** again. "
            "CivicEye will automatically try several backup mirrors."
        )
        return

    if not address_rows:
        st.warning("No addresses found for that ZIP code and house number combination.")
        return

    candidates: List[AddressCandidate] = []
    for index, row in enumerate(address_rows):
        map_data = fetch_map_image_for_location(row["lat"], row["lon"])
        map_url = str(map_data.get("url") or "")
        map_provider = str(map_data.get("provider") or "Static map service")
        map_bytes = map_data.get("image")
        map_error = map_data.get("error")

        candidate = AddressCandidate(
            id=f"{row['lat']:.6f}|{row['lon']:.6f}|{index}",
            street=str(row["street"]),
            city=str(row["city"]) if row.get("city") else None,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            map_url=map_url,
            map_provider=map_provider,
            map_image=map_bytes,
            map_error=map_error,
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


def render_card_grid(
    candidates: List[AddressCandidate], selected_id: str, cards_per_row: int
) -> None:
    """Render the map cards in a responsive grid."""
    if not candidates:
        return

    cols_per_row = max(1, cards_per_row)
    for start in range(0, len(candidates), cols_per_row):
        row_candidates = candidates[start : start + cols_per_row]
        columns = st.columns(len(row_candidates))
        for column, candidate in zip(columns, row_candidates):
            with column:
                if candidate.map_image:
                    st.image(candidate.map_image, width="stretch")
                elif candidate.map_error:
                    if "not configured" in candidate.map_error.lower():
                        st.info("Add a Google Maps Static API key to view map previews.")
                    else:
                        st.warning(candidate.map_error)
                else:
                    st.warning("Map preview unavailable.")

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

    cards_per_row = st.slider(
        "Cards per row",
        min_value=1,
        max_value=4,
        value=3,
        help="Adjust how many address cards appear per row.",
    )

    render_card_grid(candidates, selected_id, cards_per_row)

    selected_candidate = next(
        candidate for candidate in candidates if candidate.id == selected_id
    )

    try:
        st.session_state[SESSION_CAROUSEL_INDEX_KEY] = candidates.index(selected_candidate)
    except ValueError:
        st.session_state[SESSION_CAROUSEL_INDEX_KEY] = 0

    render_carousel(candidates)

    st.divider()
    st.subheader("Selected address")
    st.write(
        f"{selected_candidate.street}"
        + (f", {selected_candidate.city}" if selected_candidate.city else "")
    )
    st.write(f"Coordinates: {selected_candidate.lat:.6f}, {selected_candidate.lon:.6f}")
    st.caption(f"Map provider: {selected_candidate.map_provider}")

    if selected_candidate.map_image:
        st.image(selected_candidate.map_image, caption="Preview", width="stretch")
    elif selected_candidate.map_error:
        if "not configured" in selected_candidate.map_error.lower():
            st.info("Add a Google Maps Static API key to view map previews.")
        else:
            st.warning(selected_candidate.map_error)
    else:
        st.warning("Map preview unavailable for this address.")

    maps_link = f"https://www.google.com/maps?q={selected_candidate.lat},{selected_candidate.lon}"
    st.link_button("Open in Google Maps", maps_link)


def render_api_key_manager() -> Optional[str]:
    """Allow the user to view, set, or update the Google Maps API key."""
    current_key = get_google_maps_api_key()
    default_expand = current_key is None

    with st.expander(
        "Google Maps Static API configuration",
        expanded=default_expand,
    ):
        st.markdown(
            "Provide a Google Maps Static API key to enable high quality map previews. "
            "You can create one in the [Google Cloud Console]"
            "(https://developers.google.com/maps/documentation/static-maps/get-api-key)."
        )
        st.caption(
            "The key is stored locally in `.streamlit/google_maps_api_key.txt` so you "
            "don't have to re-enter it on every run."
        )

        api_key_input = st.text_input(
            "Google Maps Static API key",
            type="password",
            key="google_api_key_input",
        )
        save_clicked = st.button("Save API Key", key="save_google_api_key")
        if save_clicked:
            if api_key_input.strip():
                save_google_maps_api_key(api_key_input.strip())
                st.session_state[SESSION_API_KEY_SAVED_FLAG] = True
                st.success("Google Maps API key saved locally.")
                st.cache_data.clear()
                current_key = api_key_input.strip()
                st.experimental_rerun()
            else:
                st.error("Please enter a valid API key before saving.")

        if current_key:
            st.caption("Current key loaded successfully.")

    return get_google_maps_api_key()


def render_carousel(candidates: List[AddressCandidate]) -> None:
    """Display a simple carousel to browse candidate map images."""
    if not candidates:
        return

    index = st.session_state.get(SESSION_CAROUSEL_INDEX_KEY, 0)
    index = max(0, min(index, len(candidates) - 1))
    candidate = candidates[index]

    st.subheader("Quick preview carousel")
    columns = st.columns([1, 6, 1])
    with columns[0]:
        if st.button("◀", disabled=len(candidates) <= 1, key="carousel_prev"):
            st.session_state[SESSION_CAROUSEL_INDEX_KEY] = (index - 1) % len(candidates)
            st.experimental_rerun()
    with columns[2]:
        if st.button("▶", disabled=len(candidates) <= 1, key="carousel_next"):
            st.session_state[SESSION_CAROUSEL_INDEX_KEY] = (index + 1) % len(candidates)
            st.experimental_rerun()

    with columns[1]:
        st.markdown(
            f"**{candidate.street}"
            f"{', ' + candidate.city if candidate.city else ''}** "
            f"({index + 1}/{len(candidates)})"
        )
        if candidate.map_image:
            st.image(candidate.map_image, width="stretch")
        elif candidate.map_error:
            st.warning(candidate.map_error)
        elif candidate.map_url:
            st.image(candidate.map_url, width="stretch")
        else:
            st.warning("Map preview unavailable.")


def render_search_form() -> None:
    """Render the user input form."""
    api_key = render_api_key_manager()
    if not api_key:
        st.warning(
            "Map previews will remain blank until a Google Maps Static API key is configured."
        )

    st.caption(
        "Map previews leverage Google Street View whenever available and fall back to the "
        "Google Maps Static API. Address results are still derived from OpenStreetMap."
    )
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
