# CivicEye

CivicEye streamlines the process of validating German civic numbers against OpenStreetMap. Provide a ZIP code (`PLZ`) and a house number (`Hausnummer`) and the app lists every matching object, complete with static map thumbnails. If you also upload a reference photo, CLIP embeddings rank the most similar locations.

## Why CivicEye?
- **Comprehensive search** – find every OpenStreetMap entry matching your civic number.
- **Map-driven review** – inspect candidates visually using OpenStreetMap’s static tiles (no API key required).
- **Visual similarity** – optional CLIP ranking brings the most likely matches to the top.
- **Streamlit UX** – a clean, multi-step interface that guides users from search to confirmation.

## Quickstart
```bash
uv venv .venv
source .venv/bin/activate
pip install -e .[viz]
streamlit run main.py
```

Fill out the ZIP and house number fields, optionally upload a JPG/PNG, and select a result. The selected card links back out to Google Maps for final verification.

## Project layout
```
src/civiceye/
├── clip/                # CLIP similarity helpers
├── openmaps/            # Overpass querying & OSM static map utilities
└── streamlit_app/       # Streamlit page configuration and UI
```

`main.py` simply bootstraps the package so `streamlit run main.py` works out of the box.

## Optional CLIP dependencies
Install the `viz` extra (or the individual packages) to enable similarity scoring:
```bash
pip install -e .[viz]
```

Without these libraries, CivicEye still retrieves addresses and maps—only the ranking feature is disabled.

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
