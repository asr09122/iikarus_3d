import os
import json
from typing import List, Dict, Any, Union, Optional

from dotenv import load_dotenv
from pinecone import Pinecone

# Optional: local embeddings (default)
from sentence_transformers import SentenceTransformer

# Optional: Space embeddings if you want to pull from your HF Space
try:
    from gradio_client import Client as GradioClient
except Exception:
    GradioClient = None  # only needed if USE_SPACE_EMBED=true

# --- Load .env safely (optional for local dev) ---
load_dotenv()

# --- ENV variables ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "product-recommendations")

# Embedding config
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-mpnet-base-v2")
USE_SPACE_EMBED = os.getenv("USE_SPACE_EMBED", "false").lower() in {"1", "true", "yes"}
IKARUS_SPACE = os.getenv("IKARUS_SPACE", "asr3232/ikarus_3d")

# --- Validation ---
if not PINECONE_API_KEY:
    raise RuntimeError("❌ Missing PINECONE_API_KEY in your .env file.")

print(f"✅ Using Pinecone index: {PINECONE_INDEX}")
print(f"✅ Embedding source: {'HF Space /embed_fn' if USE_SPACE_EMBED else EMBED_MODEL}")

# --- Initialize Pinecone ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# --- Embedding providers ---
_embedder: Optional[SentenceTransformer] = None
_space_client: Optional[GradioClient] = None

if USE_SPACE_EMBED:
    if GradioClient is None:
        raise RuntimeError("USE_SPACE_EMBED=true but gradio_client is not installed. `pip install gradio_client`")
    _space_client = GradioClient(IKARUS_SPACE)
else:
    _embedder = SentenceTransformer(EMBED_MODEL)


def _coerce_json(x: Any):
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return x
    return x


# --- Core functions ---
def embed_text(text: str) -> List[float]:
    """
    Convert query text into a vector.
    - Default: SentenceTransformer local model
    - If USE_SPACE_EMBED=true: calls Space /embed_fn (expects [{ "embeddings": [[...]] }])
    """
    if not text:
        return []

    if USE_SPACE_EMBED and _space_client:
        res: Union[List, Dict, str] = _space_client.predict(
            multiline_text=text,
            normalize=True,
            api_name="/embed_fn",
        )
        res = _coerce_json(res)

        # Expected primary shape: list with dict containing "embeddings": [[...]]
        if isinstance(res, list) and res and isinstance(res[0], dict):
            emb = res[0].get("embeddings") or res[0].get("embedding")
            if isinstance(emb, list):
                vec = emb[0] if emb and isinstance(emb[0], list) else emb
                return [float(v) for v in vec]

        # Fallbacks
        if isinstance(res, dict):
            emb = res.get("embeddings") or res.get("embedding") or res.get("vector") or res.get("data")
            if isinstance(emb, list):
                vec = emb[0] if emb and isinstance(emb[0], list) else emb
                return [float(v) for v in vec]

        if isinstance(res, list) and res and isinstance(res[0], (int, float)):
            return [float(v) for v in res]

        raise ValueError(f"Unexpected /embed_fn response shape: {type(res)} -> {res}")

    # Local model path
    return _embedder.encode(text).tolist()


def query_index(vec: List[float], top_k: int) -> Dict[str, Any]:
    """Search Pinecone index for similar items based on embedding vector."""
    return index.query(vector=vec, top_k=top_k, include_metadata=True)


def fetch_by_ids(ids: List[str]) -> Dict[str, Any]:
    """Fetch metadata for given vector IDs."""
    return index.fetch(ids=ids)
