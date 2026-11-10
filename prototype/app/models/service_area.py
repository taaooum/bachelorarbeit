from pydantic import BaseModel, Field

class ServiceArea(BaseModel):
    """
    One service area in the outline (Grobgliederung), before the plan is worked out.
    """
    title: str = Field(
        description="""Kurze Bezeichnung des Leistungsbereichs."""
    )
    description: str = Field(
        description="""Ein bis zwei Sätze, die die betroffenen Systeme,
        Technologien und Tätigkeiten konkret benennen. Dieser Text wird als
        Suchanfrage gegen abgeschlossene Projekte verwendet."""
    )