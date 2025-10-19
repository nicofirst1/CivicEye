# CivicEye

CivicEye streamlines the process of validating German civic numbers against OpenStreetMap. Provide a ZIP code (`PLZ`) and a house number (`Hausnummer`) and the app lists every matching object, complete with static map thumbnails. If you also upload a reference photo, CLIP embeddings rank the most similar locations.

## Why CivicEye?
- **Comprehensive search** – find every OpenStreetMap entry matching your civic number.
- **Street-level review** – browse Google Street View imagery (with static map fallback) right inside the app.
- **Visual similarity** – optional CLIP ranking brings the most likely matches to the top.
- **Streamlit UX** – a clean, multi-step interface that guides users from search to confirmation.

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.tt
streamlit run main.py
```

Fill out the ZIP and house number fields, optionally upload a JPG/PNG, and select a result. On first launch you’ll be prompted for a Google Maps Static API key (stored locally in `.streamlit/google_maps_api_key.txt`). The selected card links back out to Google Maps for final verification.

## Project layout
```
src/civiceye/
├── clip/                # CLIP similarity helpers
├── openmaps/            # Overpass querying & Google static map helpers
└── streamlit_app/       # Streamlit page configuration and UI
```

`main.py` simply bootstraps the package so `streamlit run main.py` works out of the box.

## Optional CLIP dependencies
Install the CLIP stack (`torch`, `transformers`, `sentence-transformers`) to enable similarity scoring:
```bash
pip install torch transformers sentence-transformers
```

Without these libraries, CivicEye still retrieves addresses and maps—only the ranking feature is disabled.

## Google Maps Static API key
CivicEye renders map previews through the Google Maps Static API. When no key is detected the app prompts you for one and saves it locally. You can create a key in the [Google Cloud Console](https://developers.google.com/maps/documentation/static-maps/get-api-key) and paste it into the UI. Delete `.streamlit/google_maps_api_key.txt` if you ever need to reset the stored key.

## Deploying to GitHub Pages
This repository ships with a MkDocs configuration (`mkdocs.yml`) and a GitHub Actions workflow that publishes the documentation to GitHub Pages:

1. Push your changes to GitHub.
2. Ensure GitHub Actions is enabled.
3. After the workflow runs, open the repository settings → *Pages*, and select the `gh-pages` branch.

The documentation will be available at `https://<your-username>.github.io/<repository>/`.

## Need more?
- Streamlit documentation: https://docs.streamlit.io/
- OpenStreetMap Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API
- CLIP model (openai/clip-vit-base-patch32): https://huggingface.co/openai/clip-vit-base-patch32
