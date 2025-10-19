## CivicEye

CivicEye is a Streamlit application that helps you visually confirm street addresses that share the same postal code (PLZ) and civic number. The app queries OpenStreetMap’s Overpass API, renders map thumbnails for every match, and—if you provide a reference photo—uses CLIP embeddings to rank the best visual candidates.

You can use use it
[on streamlit](https://civiceye.streamlit.app/)

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
└── requirements.tt                 # Runtime dependencies
```

### Getting started
1. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install requirements**
   ```bash
   pip install -r requirements.tt
   ```
   Install the optional CLIP stack (`torch`, `transformers`, `sentence-transformers`) if you want similarity scoring.

3. **Run the app**
   ```bash
   streamlit run main.py
   ```
   Enter a German ZIP and house number to search. On the first launch, paste your Google Maps Static API key into the prompt (the key is saved in `.streamlit/google_maps_api_key.txt`). Upload a JPG/PNG if you want similarity scoring.

### Optional CLIP support
CLIP similarity requires GPU-friendly dependencies. If the model fails to load, the app continues without similarity scoring and displays a warning. You can preload the model locally to avoid runtime downloads:
```bash
python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"
```
