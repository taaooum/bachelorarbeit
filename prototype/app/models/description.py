from pydantic import BaseModel, Field

class Description(BaseModel):
    """The project description worked out with the user."""

    title: str = Field(
        description="""Kurzer Projekttitel, z.B. 'Server-Migration Musterbau GmbH'."""
    )
    description: str = Field(
        description="""Die vollständige, aktuelle Projektbeschreibung als
        Fließtext über mehrere Sätze. Übernimm alles bereits Bekannte aus
        der aktuellen Beschreibung und ergänze die neuen Angaben. Sie ersetzt
        die bisherige Beschreibung vollständig - kürze also nichts weg."""
    )