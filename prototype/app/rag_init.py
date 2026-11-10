import json
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType
from rag import rag_client, EMBEDDING_SIZE, LESSONS_LEARNED_COLLECTION, WBS_COLLECTION
from rag_ingest import ingest_lessons_learned, ingest_work_breakdown_structure

# -----------------------------------------------------------------------------
# constants and classes.

SHOULD_SEED = True

SEED_DIR = Path(__file__).resolve().parent.parent / ".seed"

LESSONS_LEARNED_FILE = SEED_DIR / "lessons_learned.json"
WORK_BREAKDOWN_STRUCTURE_FILE = SEED_DIR / "work_breakdown_structure.json"

@dataclass(frozen=True) # Immutable configuration for a Qdrant collection
class CollectionConfig:
    name: str
    vector_params: VectorParams
    payload_indices: dict[str, PayloadSchemaType]
    seed_fn: Callable[[], None]

# TODO: Evaluate on-prem or cloud embedding - https://qdrant.tech/course/essentials/day-1/embedding-models/#2-managed-and-integrated-cloud-providers


# -----------------------------------------------------------------------------
# seeding.



def _load_json(path: str | Path) -> list[dict[str, Any]]:
    """
    Load a seed file as a list of records.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def seed_work_breakdown_structure() -> None:
    """
    Loads work_breakdown_structure.json from the seed directory and ingests it.
    """
    if WORK_BREAKDOWN_STRUCTURE_FILE.exists():
        print(f"Ingesting work_breakdown_structure from {WORK_BREAKDOWN_STRUCTURE_FILE} ...")
        ingest_work_breakdown_structure(_load_json(WORK_BREAKDOWN_STRUCTURE_FILE))
    else:
        print(f"No file found at {WORK_BREAKDOWN_STRUCTURE_FILE}")

def seed_lessons_learned() -> None:
    """
    Loads lessons_learned.json from the seed directory and ingests it.
    """
    if LESSONS_LEARNED_FILE.exists():
        print(f"Ingesting lessons_learned from {LESSONS_LEARNED_FILE} ...")
        ingest_lessons_learned(_load_json(LESSONS_LEARNED_FILE))
    else:
        print(f"No file found at {LESSONS_LEARNED_FILE}")

# -----------------------------------------------------------------------------
# some constants.

COLLECTIONS: tuple[CollectionConfig, ...] =  (
    CollectionConfig(
        name=LESSONS_LEARNED_COLLECTION,
        vector_params=VectorParams(
            size=EMBEDDING_SIZE,
            distance=Distance.COSINE
        ),
        payload_indices={
            "project_number": PayloadSchemaType.KEYWORD,
            "project_manager": PayloadSchemaType.KEYWORD,
            "customer": PayloadSchemaType.KEYWORD,
            "title": PayloadSchemaType.TEXT,
            "problem": PayloadSchemaType.TEXT,
            "solution": PayloadSchemaType.TEXT,
            "project_type": PayloadSchemaType.KEYWORD,
            "project_phase": PayloadSchemaType.KEYWORD,
            "skill_team": PayloadSchemaType.KEYWORD,
            "created_by": PayloadSchemaType.KEYWORD,
            "created_at": PayloadSchemaType.DATETIME,
        },
        seed_fn=seed_lessons_learned,
    ),
    CollectionConfig(
        name=WBS_COLLECTION,
        vector_params=VectorParams(
            size=EMBEDDING_SIZE,
            distance=Distance.COSINE
        ),
        payload_indices={
            "project_number": PayloadSchemaType.KEYWORD, # z.B. V20260625-00058
            "is_managed": PayloadSchemaType.BOOL, # managed/unmanaged
            "node_type": PayloadSchemaType.KEYWORD,
            "owner": PayloadSchemaType.KEYWORD, # project manager
            "customer": PayloadSchemaType.KEYWORD,
            "billable": PayloadSchemaType.BOOL,
            "title": PayloadSchemaType.KEYWORD,
            "description": PayloadSchemaType.TEXT,
            "estimated_hours": PayloadSchemaType.FLOAT,
            "documented_hours": PayloadSchemaType.FLOAT,
        },
        seed_fn=seed_work_breakdown_structure,
    )
)


# -----------------------------------------------------------------------------
# do setup stuff.

# collections
def _resolve_collection_configs(collections: tuple[CollectionConfig, ...] | None) -> tuple[CollectionConfig, ...]:
    return collections if collections is not None else COLLECTIONS

def get_collections() -> list[str]:
    """
    Returns the names of the collections in the Qdrant database.
    """
    collections = rag_client.get_collections().collections
    collection_names = [c.name for c in collections]
    return collection_names


def create_collections(collections: tuple[CollectionConfig, ...] | None = None) -> None:
    """
    Creates and seeds all configured collections.
    """
    configs = _resolve_collection_configs(collections)

    for collection_config in configs:
        collection_name = collection_config.name
        rag_client.create_collection(
            collection_name=collection_name,
            vectors_config=collection_config.vector_params,
        )
        print(f"Collection '{collection_name}' created.")

        create_payload_indices(collection_config)
        print(f"Collection '{collection_name}' configured with payload indices.")

        seed_collections(collection_config)
        print(f"Seeding collection '{collection_name}'.")
            
def delete_collections(collections: tuple[CollectionConfig, ...] | None = None) -> None:
    """
    Deletes the collections if they exist.
    """
    existing = get_collections()
    configs = _resolve_collection_configs(collections)
    
    for collection_config in configs:
        if collection_config.name in existing:
            rag_client.delete_collection(collection_name=collection_config.name)
            print(f"Collection '{collection_config.name}' deleted.")
  
def reset_collections(collections: tuple[CollectionConfig, ...] | None = None) -> None:
    """
    Deletes and recreates the collections.
    """
    delete_collections(collections)
    create_collections(collections)

# indices
def create_payload_indices(collection: CollectionConfig | None = None) -> None:
    """
    Creates the payload indices for the collections.
    Used for filtering and searching based on payload fields.
    """
    if collection is None:
        return

    collection_name = collection.name
    for field_name, field_type in collection.payload_indices.items():
        try:
            rag_client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type
            )
            print(f"Payload index '{field_name}' created for collection '{collection_name}'.")
        except Exception as e:
            print(f"Error creating payload index '{field_name}' for collection '{collection_name}': {e}")

def seed_collections(collection: CollectionConfig) -> None:
    """
    Runs the seed function for the given collection, unless seeding is disabled via SHOULD_SEED.
    """
    if not collection:
        return

    if not SHOULD_SEED:
        print("Seeding is disabled.")
        return

    if collection.seed_fn:
        print(f"Seeding newly created collection '{collection.name}' ...")
        collection.seed_fn()
        print(f"Finished seeding collection '{collection.name}'.")
    else:
        print(f"No seed function for collection '{collection.name}' defined.")


if __name__ == "__main__":
    try:
        reset_collections()
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        raise SystemExit(1)
