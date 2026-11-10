from typing import Literal
from pydantic import BaseModel, Field
from .wbs import Wbs
from .description import Description
from .service_area import ServiceArea



class DescriptionResult(BaseModel):
    """
    One turn of the description dialogue.
    """
    response: str = Field(
        description="""Deine Antwort und Erklärungen an den Nutzer mit allen wichtigen Informationen. Entweder die Rückfragen zu fehlenden Angaben, oder (wenn alles vorliegt) eine knappe Zusammenfassung und der Vorschlag, zur Planungsphase zu wechseln. Der Chat stellt Markdown dar - nutze es für Struktur (Aufzählungen für mehrere Rückfragen oder Punkte, Fettschrift für Feldnamen/Begriffe), aber ohne Überschriften."""
    )
    description: Description = Field(
        description="""Der aktuelle Stand von Titel und Projektbeschreibung."""
    )
    phase_reasoning: str = Field(
        description="""Kurze Begründung: Welche Angaben der Liste sind erledigt
        (beantwortet oder vom Nutzer als unbekannt/nicht relevant bezeichnet),
        welche noch nicht angesprochen, will der Nutzer weitermachen?"""
    )
    phase_status: Literal["continue", "ready"] = Field(
        description="""'ready', wenn alle Angaben der Liste erledigt sind oder
        der Nutzer ausdrücklich weitermachen will. Sonst 'continue'."""
    )


class ServiceAreaResult(BaseModel):
    """
    The outline (Grobgliederung) of a plan: which service areas the project needs.

    Kept separate from Wbs because it only exists between the two generation
    steps. It carries no numbering, no tasks and no sources.
    """
    leistungsbereiche: list[ServiceArea] = Field(
        description="""Die Leistungsbereiche, in die sich das Projekt gliedert."""
    )


class WbsResult(BaseModel):
    """
    The work breakdown structure together with notes for the user.
    """
    response: str = Field(
        description="""Alles, was der Nutzer zu lesen bekommt: kurze Erläuterung
        des Plans bzw. der Änderung, offene Aufwände und Fragen, Hinweise zu
        Lessons Learned. Nicht den ganzen Plan wiederholen.
        Der Chat stellt Markdown dar - nutze es für Struktur (Aufzählungen
        je Leistungsbereich oder Lesson Learned, Fettschrift für Titel und
        Projektnummern), aber ohne Überschriften."""
    )
    work_breakdown_structure: Wbs = Field(
        description="""Der zum Plan gehörige Projektstrukturplan."""
    )
    relevant_lessons: list[str] = Field(
        default_factory=list,
        description="""Lessons Learned aus dem Verlauf, die für dieses Projekt
        relevant sind. Nur aus den bereitgestellten Kandidaten, nichts erfinden.
        Leer lassen, wenn keine gefunden wurden. Getrennt von 'sources', das nur
        Referenzprojekte enthält.""",
    )
