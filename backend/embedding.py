"""
CLIP-based image embedding + similarity utilities.

We use `sentence-transformers`'s CLIP wrapper (model: clip-ViT-B-32) because it's
much simpler to set up than raw OpenAI CLIP, and it downloads automatically the
first time it's used (needs internet on first run only; cached afterwards).
"""

import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer, util

_model = None


def get_model():
    """Lazy-load the model once (it's ~350MB, don't want to reload per-request)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("clip-ViT-B-32")
    return _model


def get_image_embedding(image_path: str):
    """Returns a 512-dim embedding vector (list[float]) for the given image path."""
    model = get_model()
    image = Image.open(image_path).convert("RGB")
    embedding = model.encode(image, convert_to_numpy=True)
    return embedding


def cosine_similarity(vec_a, vec_b) -> float:
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    return float(util.cos_sim(a, b)[0][0])


def find_top_matches(query_embedding, candidates, top_k=5, min_score=0.6):
    """
    candidates: list of (item, embedding_list) tuples
    Returns: list of (item, score) sorted by descending similarity,
             filtered to score >= min_score.
    """
    scored = []
    for item, emb in candidates:
        if emb is None:
            continue
        score = cosine_similarity(query_embedding, emb)
        if score >= min_score:
            scored.append((item, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
