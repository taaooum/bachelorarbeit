from typing import Any
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Filter
import os

LITELLM_BASE_URL = os.environ.get("LITELLM_URL", "http://localhost:8080")

LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "admin")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "ollama/bge-m3")
EMBEDDING_SIZE = int(os.environ.get("EMBEDDING_SIZE", "1024"))  # bge-m3 -> 1024 dims
EMBEDDING_TIMEOUT = float(os.environ.get("EMBEDDING_TIMEOUT", "180")) # Time until the embedding request times out

WBS_COLLECTION = "work_breakdown_structure"
LESSONS_LEARNED_COLLECTION = "lessons_learned"

rag_client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

# -----------------------------------------------------------------------------
# embed texts


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts via LiteLLM.
    """
    if not texts:
        return []
    
    response = requests.post(
        f"{LITELLM_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=EMBEDDING_TIMEOUT,
    )
    
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in data]


# -----------------------------------------------------------------------------
# search for relevant points

def _search(
    collection_name: str,
    query: str,
    top_k: int,
    query_filter: Filter | None = None,
) -> list[dict[str, Any]]:
    """
    Run a vector search against a single collection and return the hits
    with id, score and payload.

    The optional filter narrows the search by payload fields, for example
    by customer or project type.
    """
    query_vector = embed_texts([query])[0]

    response = rag_client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    return [
        {"id": point.id, "score": point.score, "payload": point.payload}
        for point in response.points
    ]


def search_relevant_work_breakdown_structures(
    query: str,
    top_k: int = 5,
    query_filter: Filter | None = None,
) -> list[dict[str, Any]]:
    """
    Search for service areas of completed projects that match the query.
    """
    return _search(WBS_COLLECTION, query, top_k, query_filter)


def search_relevant_lessons_learned(
    query: str,
    top_k: int = 5,
    query_filter: Filter | None = None,
) -> list[dict[str, Any]]:
    """
    Search for lessons learned that match the query.
    """
    return _search(LESSONS_LEARNED_COLLECTION, query, top_k, query_filter)
