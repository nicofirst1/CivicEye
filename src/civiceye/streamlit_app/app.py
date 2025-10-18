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

MAX_ADDRESS_RESULTS = 100
DEFAULT_CARD_WIDTH = 260

SESSION_RESULTS_KEY = "civiceye_results"
SESSION_SELECTED_ID_KEY = "civiceye_selected_id"
SESSION_HAS_SIMILARITY_KEY = "civiceye_has_similarity"
SESSION_API_KEY_SAVED_FLAG = "civiceye_api_key_saved"
SESSION_CARD_WIDTH_KEY = "civiceye_card_width"


def configure_page() -> None:
    st.set_page_config(page_title="CivicEye", page_icon="👁️", layout="wide")
    st.markdown(
        """
        <style>
        .hero-box {
            background: linear-gradient(120deg, #6A0D83, #EE5D6C);
            color: #F8F2EB;
            padding: 1.8rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
        }
        .hero-box h1 {
            margin: 0 0 0.6rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_intro(api_key_present: bool) -> None:
    st.markdown(
        """
        <div class="hero-box">
            <h1>👁️ CivicEye</h1>
            <p>
                Real-estate listings often hide the exact address. Enter the postal code and house
                number you spotted in a photo, and CivicEye will list every OpenStreetMap entry that matches.
                Compare the images to pinpoint the real location.
            </p>
            <ul>
                <li>Drop the postal code and house number you found.</li>
                <li>Review every OpenStreetMap match for that combination.</li>
                <li>Visually confirm the building with static imagery or Street View.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not api_key_present:
        st.info("Scroll down to connect a Google Maps API key to enable Street View previews.")


def handle_search(
    zip_code: str, house_number: str, uploaded_image, progress_bar
) -> None:
    st.session_state.pop(SESSION_RESULTS_KEY, None)
    st.session_state.pop(SESSION_SELECTED_ID_KEY, None)
    st.session_state.pop(SESSION_HAS_SIMILARITY_KEY, None)
    st.session_state[SESSION_CARD_WIDTH_KEY] = DEFAULT_CARD_WIDTH
    st.session_state["results_capped"] = False

    progress_bar.progress(5, text="Contacting OpenStreetMap…")

    try:
        address_rows = fetch_addresses(zip_code, house_number)
    except requests.RequestException as exc:
        progress_bar.progress(100, text="Search failed")
        st.error(f"Failed to query Overpass API: {exc}")
        st.info(
            "The Overpass API occasionally times out under heavy load. "
            "Wait a minute and press **Search Addresses** again."
        )
        return

    if not address_rows:
        progress_bar.progress(100, text="No matches found")
        st.warning("No addresses found for that combination.")
        return

    progress_bar.progress(25, text="Loading map previews…")
    candidates: List[AddressCandidate] = []
    limited_rows = address_rows[:MAX_ADDRESS_RESULTS]
    for index, row in enumerate(limited_rows):
        map_data = fetch_map_image_for_location(row["lat"], row["lon"])
        candidate = AddressCandidate(
            id=f"{row['lat']:.6f}|{row['lon']:.6f}|{index}",
            street=str(row["street"]),
            city=str(row["city"]) if row.get("city") else None,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            map_url=str(map_data.get("url") or ""),
            map_provider=str(map_data.get("provider") or "Static imagery"),
            map_image=map_data.get("image"),
            map_error=map_data.get("error"),
        )
        candidates.append(candidate)
        if progress_bar:
            fraction = (index + 1) / max(len(limited_rows), 1)
            progress_bar.progress(
                25 + int(fraction * 45), text="Processing map imagery…"
            )

    if len(address_rows) > MAX_ADDRESS_RESULTS:
        st.session_state["results_capped"] = True
        st.info(
            f"Showing the first {MAX_ADDRESS_RESULTS} matches. "
            "Use the dropdown to inspect individual locations."
        )

    if uploaded_image:
        progress_bar.progress(80, text="Computing similarity scores…")
        candidates = compute_similarity_scores(uploaded_image, candidates)
        st.session_state[SESSION_HAS_SIMILARITY_KEY] = True
    else:
        st.session_state[SESSION_HAS_SIMILARITY_KEY] = False

    st.session_state[SESSION_RESULTS_KEY] = candidates
    progress_bar.progress(100, text="Search complete")


def render_card_grid(
    candidates: List[AddressCandidate], selected_id: str, card_width: int
) -> None:
    if not candidates:
        return

    gutter = 16
    approx_width = 940  # rough main column width
    columns_per_row = max(1, int(approx_width / max(card_width + gutter, 1)))

    for start in range(0, len(candidates), columns_per_row):
        row_candidates = candidates[start : start + columns_per_row]
        columns = st.columns(len(row_candidates), gap="small")
        for column, candidate in zip(columns, row_candidates):
            with column:
                if candidate.map_image:
                    st.image(candidate.map_image, width=card_width)
                elif candidate.map_url:
                    st.image(candidate.map_url, width=card_width)
                elif candidate.map_error:
                    st.info(candidate.map_error)
                else:
                    st.info("Map preview unavailable.")

                street_line = candidate.street
                if candidate.city:
                    street_line += f", {candidate.city}"
                st.write(street_line)
                st.caption(f"{candidate.lat:.5f}, {candidate.lon:.5f}")

                if candidate.similarity is not None:
                    st.caption(f"Similarity score: {candidate.similarity:.2f}")

                st.button(
                    "Selected" if candidate.id == selected_id else "Select",
                    key=f"select_btn_{candidate.id}",
                    disabled=candidate.id == selected_id,
                    use_container_width=True,
                    on_click=(
                        None
                        if candidate.id == selected_id
                        else lambda cid=candidate.id: st.session_state.update(
                            {SESSION_SELECTED_ID_KEY: cid}
                        )
                    ),
                )


def display_results() -> None:
    candidates: List[AddressCandidate] = st.session_state.get(SESSION_RESULTS_KEY, [])
    if not candidates:
        return

    has_similarity = st.session_state.get(SESSION_HAS_SIMILARITY_KEY, False)
    results_capped = st.session_state.get("results_capped", False)

    st.subheader(f"Found {len(candidates)} possible addresses")
    if has_similarity:
        st.caption(
            "Results are ordered by cosine similarity with the uploaded reference image."
        )

    option_labels = {
        candidate.id: f"{candidate.street}"
        + (f", {candidate.city}" if candidate.city else "")
        for candidate in candidates
    }
    option_ids = list(option_labels.keys())
    default_id = st.session_state.get(SESSION_SELECTED_ID_KEY, option_ids[0])
    index = option_ids.index(default_id) if default_id in option_ids else 0

    with st.expander("Explore matches", expanded=True):
        selected_id = st.selectbox(
            "Select an address to inspect",
            options=option_ids,
            index=index,
            format_func=lambda cid: option_labels.get(cid, cid),
            key=SESSION_SELECTED_ID_KEY,
        )

        card_width = st.slider(
            "Thumbnail width",
            min_value=180,
            max_value=480,
            step=20,
            value=st.session_state.get(SESSION_CARD_WIDTH_KEY, DEFAULT_CARD_WIDTH),
            help="Control how wide each preview appears.",
        )
        st.session_state[SESSION_CARD_WIDTH_KEY] = card_width

        if results_capped:
            st.info(
                "Preview grid disabled because too many matches were returned. "
                "Use the dropdown to inspect individual entries."
            )
        else:
            render_card_grid(candidates, selected_id, card_width)

    selected_candidate = next(
        candidate for candidate in candidates if candidate.id == selected_id
    )

    st.subheader("Selected address")
    street_line = selected_candidate.street
    if selected_candidate.city:
        street_line += f", {selected_candidate.city}"
    st.write(street_line)
    st.write(f"Coordinates: {selected_candidate.lat:.6f}, {selected_candidate.lon:.6f}")
    st.caption(f"Imagery provider: {selected_candidate.map_provider}")

    if not results_capped:
        if selected_candidate.map_image:
            st.image(selected_candidate.map_image, caption="Preview", width=420)
        elif selected_candidate.map_error:
            st.info(selected_candidate.map_error)
        else:
            st.info("Map preview unavailable for this address.")
    else:
        st.info(
            f"Preview disabled when more than {MAX_ADDRESS_RESULTS} matches are returned."
        )

    maps_link = f"https://www.google.com/maps?q={selected_candidate.lat},{selected_candidate.lon}"
    st.link_button("Open in Google Maps", maps_link)


def render_api_key_manager() -> Optional[str]:
    current_key = get_google_maps_api_key()
    expanded = current_key is None

    with st.expander("Google Maps imagery configuration", expanded=expanded):
        st.write(
            "Street View previews require a Google Maps API key. "
            "Create one in the Google Cloud Console and paste it here."
        )

        api_key_input = st.text_input(
            "Google Maps API key", type="password", key="google_api_key_input"
        )
        if st.button("Save API key"):
            if api_key_input.strip():
                save_google_maps_api_key(api_key_input.strip())
                st.session_state[SESSION_API_KEY_SAVED_FLAG] = True
                st.success("API key saved locally.")
                st.cache_data.clear()
            else:
                st.error("Please enter a valid API key.")

        if current_key:
            st.caption("A Google Maps API key is already configured.")

    return get_google_maps_api_key()


def render_search_form() -> None:
    with st.form("search_form"):
        zip_code = st.text_input("Postal code (ZIP / PLZ)")
        house_number = st.text_input("House number")
        uploaded_image = st.file_uploader(
            "Optional reference photo (JPG or PNG)",
            type=["png", "jpg", "jpeg"],
        )
        submitted = st.form_submit_button("Search addresses")

    if submitted:
        if not zip_code or not house_number:
            st.error("Please provide both a postal code and a house number.")
            return

        progress_bar = st.progress(0, text="Starting search…")
        try:
            handle_search(zip_code.strip(), house_number.strip(), uploaded_image, progress_bar)
        finally:
            progress_bar.empty()


def render_footer() -> None:
    st.caption("Made with curiosity by Nicolo' Brandizzi — https://nicofirst1.github.io/")


def main() -> None:
    configure_page()
    current_key = get_google_maps_api_key()
    render_intro(api_key_present=bool(current_key))
    api_key_present = render_api_key_manager() is not None
    render_search_form()
    display_results()
    render_footer()


if __name__ == "__main__":
    main()
