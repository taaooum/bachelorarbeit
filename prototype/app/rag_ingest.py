from uuid import uuid4
from typing import Any, Iterable
from qdrant_client.http.models import PointStruct
from rag import rag_client, embed_texts, LESSONS_LEARNED_COLLECTION, WBS_COLLECTION


# -----------------------------------------------------------------------------
# helpers.

def _generate_id() -> str:
    return str(uuid4())

def _batched(iterable: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i + batch_size]

def _extract_leistungsbereiche(hauptvorgang: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extracts the Leistungsbereich nodes from one Hauptvorgang.
    """
    project_data = {
        "customer": hauptvorgang.get("customer"),
        "owner": hauptvorgang.get("owner"),
        "is_managed": hauptvorgang.get("is_managed"),
    }

    result = []
    leistungsbereiche = hauptvorgang.get("children", [])

    for leistungsbereich in leistungsbereiche:
        if not leistungsbereich.get("node_type") == "Leistungsbereich":
            continue
        
        leistungsbereich = {
            **project_data,
            **leistungsbereich,
        }
        
        result.append(leistungsbereich)

    return result

# -----------------------------------------------------------------------------
# do the magic.

def ingest_lessons_learned(records: list[dict[str, Any]], batch_size: int = 64) -> None:
    """
    Ingests the lessons learned data into the Qdrant database. 
    """
    if not records:
        return
    
    u = 0
    for batch in _batched(records, batch_size):
        texts_to_embed = [record["title"] + " " + record["problem"] + " " + record["solution"] for record in batch]
        vectors = embed_texts(texts_to_embed)
        
        points = []
        for record, vector in zip(batch, vectors):
            points.append(
                PointStruct(
                    id=_generate_id(),
                    vector=vector,
                    payload={
                        "project_number": record.get("project_number"),
                        "project_manager": record.get("project_manager"),
                        "customer": record.get("customer"),
                        "title": record.get("title"),
                        "problem": record.get("problem"),
                        "solution": record.get("solution"),
                        "project_type": record.get("project_type"),
                        "project_phase": record.get("project_phase"),
                        "skill_team": record.get("skill_team"),
                        "created_by": record.get("created_by"),
                        "created_at": record.get("created_at"),
                    },
                )
            )
            u += 1

        rag_client.upsert(
            collection_name=LESSONS_LEARNED_COLLECTION,
            points=points
        )

    print(f"Upserted {u} points into collection '{LESSONS_LEARNED_COLLECTION}'.")



def ingest_work_breakdown_structure(records: list[dict[str, Any]], batch_size: int = 64) -> None:
    """
    Ingests completed projects into the Qdrant database.
    """
    if not records:
        return

    leistungsbereiche: list[dict[str, Any]] = []
    for hauptvorgang in records:
        leistungsbereiche.extend(_extract_leistungsbereiche(hauptvorgang))

    if not leistungsbereiche:
        return

    u = 0
    for batch in _batched(leistungsbereiche, batch_size):
        texts_to_embed = [record["description"] for record in batch]
        vectors = embed_texts(texts_to_embed)

        points = []
        for record, vector in zip(batch, vectors):
            points.append(
                PointStruct(
                    id=_generate_id(),
                    vector=vector,
                    payload={
                        "project_number": record.get("project_number"),
                        "is_managed": record.get("is_managed"),
                        "node_type": record.get("node_type"),
                        "owner": record.get("owner"),
                        "customer": record.get("customer"),
                        "billable": record.get("billable"),
                        "title": record.get("title"),
                        "description": record.get("description"),
                        "estimated_hours": record.get("estimated_hours"),
                        "documented_hours": record.get("documented_hours"),
                        "children": record.get("children", []),
                    },
                )
            )
            u += 1

        rag_client.upsert(
            collection_name=WBS_COLLECTION,
            points=points
        )

    print(f"Upserted {u} points into collection '{WBS_COLLECTION}'.")
