## CivicEye

CivicEye is a Streamlit application that helps you visually confirm German street addresses that share the same postal code (PLZ) and civic number (Hausnummer). The app queries OpenStreetMap’s Overpass API, renders map thumbnails for every match, and—if you provide a reference photo—uses CLIP embeddings to rank the best visual candidates.

### Features
- **Address discovery** – search OpenStreetMap for every object that matches a PLZ + Hausnummer pair.
- **Street-level previews** – render Google Street View images when available, falling back to Google Static Maps if necessary.
- **Visual matching (optional)** – upload a photo and let CLIP similarity scores surface the top matches.
- **One-click selection** – review candidates in a gallery, pick your choice, and open it directly in Google Maps.

### Project layout
```
.
├── main.py                         # Streamlit entry point
├── src/civiceye
│   ├── clip/similarity.py          # CLIP embeddings and cosine similarity helpers
│   ├── openmaps/                   # Overpass + static map utilities and models
│   └── streamlit_app/app.py        # Page setup, session flow, and UI rendering
├── docs/                           # MkDocs documentation for GitHub Pages
├── mkdocs.yml                      # MkDocs configuration
└── pyproject.toml                  # Project metadata and dependencies
```

### Getting started
1. **Create a virtual environment**
   ```bash
   uv venv .venv
   source .venv/bin/activate
   ```
   > You can also use `python -m venv .venv` if you do not have `uv` installed.

2. **Install requirements**
   ```bash
   pip install -e .[viz]
   ```
   The `viz` extra pulls in the CLIP stack (`torch`, `transformers`, `sentence-transformers`). Skip it if you only need address search and maps:
   ```bash
   pip install -e .
   ```

3. **Run the app**
   ```bash
   streamlit run main.py
   ```
   Enter a German ZIP and house number to search. On the first launch, paste your Google Maps Static API key into the prompt (the key is saved in `.streamlit/google_maps_api_key.txt`). Upload a JPG/PNG if you want similarity scoring.

### Deployment options
- **Streamlit Community Cloud** – push this repo to GitHub, create a new Streamlit app, and point it at `main.py`.
- **Docker** – add your preferred base image (e.g., `python:3.11-slim`), install the project, and run `streamlit run main.py`.
- **GitHub Pages (docs)** – MkDocs builds a static documentation site. The included GitHub Actions workflow publishes `docs/` to the `gh-pages` branch. Enable GitHub Pages in repo settings and choose the `gh-pages` branch.

### Optional CLIP support
CLIP similarity requires GPU-friendly dependencies. If the model fails to load, the app continues without similarity scoring and displays a warning. You can preload the model locally to avoid runtime downloads:
```bash
python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"
```

### Development hints
- Streamlit caches API responses (`st.cache_data`) and model loads (`st.cache_resource`). Clear cache with `streamlit run main.py --clear_cache` if you suspect stale data.
- When adding new modules, keep them in `src/civiceye` to take advantage of the existing package layout.
- Store your Google Maps Static API key once and it will be reused on subsequent runs; remove `.streamlit/google_maps_api_key.txt` to reset.

### License
Released under the MIT License. See [LICENSE](LICENSE) for details.
