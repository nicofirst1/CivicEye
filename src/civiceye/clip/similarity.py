from io import BytesIO
from typing import Any, List, Optional

import streamlit as st
import torch
from PIL import Image

from ..openmaps.models import AddressCandidate

try:
    from transformers import CLIPModel, CLIPProcessor
except ImportError:
    CLIPModel = None  # type: ignore[assignment]
    CLIPProcessor = None  # type: ignore[assignment]


@st.cache_resource(show_spinner=False)
def load_clip_model() -> Optional[tuple[Any, Any]]:
    """Load the CLIP model once per session; returns None if unavailable."""
    if CLIPModel is None or CLIPProcessor is None:
        return None
    try:
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    except Exception:
        return None
    return model, processor


def ensure_rgb(image: Image.Image) -> Image.Image:
    """Convert any PIL image to RGB."""
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def compute_similarity_scores(
    uploaded_image, candidates: List[AddressCandidate]
) -> List[AddressCandidate]:
    """Compute cosine similarity between uploaded image and each map image."""
    model_bundle = load_clip_model()
    if not model_bundle:
        st.warning("Visual similarity requires the `transformers` package with CLIP support.")
        return candidates

    model, processor = model_bundle

    target_bytes = uploaded_image.getvalue()
    uploaded_image.seek(0)
    target_img = ensure_rgb(Image.open(BytesIO(target_bytes)))

    with torch.inference_mode():
        target_emb = model.get_image_features(
            **processor(images=target_img, return_tensors="pt")
        )
        target_emb = target_emb / target_emb.norm(dim=-1, keepdim=True)

    for candidate in candidates:
        if not candidate.map_image:
            candidate.similarity = None
            continue

        map_img = ensure_rgb(Image.open(BytesIO(candidate.map_image)))

        with torch.inference_mode():
            img_emb = model.get_image_features(
                **processor(images=map_img, return_tensors="pt")
            )
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
            candidate.similarity = torch.cosine_similarity(target_emb, img_emb).item()

    return sorted(
        candidates,
        key=lambda item: item.similarity if item.similarity is not None else -1.0,
        reverse=True,
    )
