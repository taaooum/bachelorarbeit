from pydantic import BaseModel, Field, model_validator


class Aufgabe(BaseModel):
    """
    A single task. The smallest unit of the plan.
    """
    key: str = Field(
        description="""Gliederungsnummer nach Ebene, z.B. '1.2.3' wenn ein Arbeitspaket darüber liegt und '1.2' wenn nicht"""
    )
    title: str = Field(
        description="""Kurze Bezeichnung der Aufgabe"""
    )
    description: str = Field(
        description="""Abschnitte 'Aufwand:', 'Leistung:' und bei Bedarf 'Ressourcen:'
        (Format siehe Systemprompt). Auf Aufgabenebene knapp: ein Satz oder wenige
        Stichpunkte je Abschnitt."""
    )
    sources: list[str] = Field(
        default_factory=list,
        description="""Historische Referenzprojekte, aus denen diese Aufgabe
        übernommen oder abgeleitet wurde. Ein Eintrag pro Projekt im Format
        'project_number - customer - title', z.B. 'PRJ-1234 - Musterbau GmbH -
        Server-Migration'. Nur mit Angaben aus den bereitgestellten
        Referenzprojekten füllen, nichts erfinden. Leer lassen, wenn kein
        Referenzprojekt vorlag.""",
    )


class Arbeitspaket(BaseModel):
    """
    An optional grouping level between service area and task.
    """
    key: str = Field(
        description="""Gliederungsnummer, z.B. '1.2'"""
    )
    title: str = Field(
        description="""Kurze Bezeichnung des Arbeitspakets"""
    )
    description: str = Field(
        description="""Abschnitte 'Aufwand:', 'Leistung:' und bei Bedarf 'Ressourcen:'
        (Format siehe Systemprompt). Auf Arbeitspaketebene knapp: ein Satz oder
        wenige Stichpunkte je Abschnitt."""
    )
    aufgaben: list[Aufgabe] = Field(
        default_factory=list,
        description="""Aufgaben in diesem Arbeitspaket""",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="""Historische Referenzprojekte, aus denen dieses
        Arbeitspaket übernommen oder abgeleitet wurde. Ein Eintrag pro Projekt
        im Format 'project_number - customer - title', z.B. 'PRJ-1234 -
        Musterbau GmbH - Server-Migration'. Nur mit Angaben aus den
        bereitgestellten Referenzprojekten füllen, nichts erfinden. Leer
        lassen, wenn kein Referenzprojekt vorlag.""",
    )


class Leistungsbereich(BaseModel):
    """
    A service area. Holds tasks directly, or work packages if it is large.
    """
    key: str = Field(
        description="""Gliederungsnummer, z.B. '1'"""
    )
    title: str = Field(
        description="""Kurze Bezeichnung des Leistungsbereichs"""
    )
    description: str = Field(
        description="""Abschnitte 'Aufwand:', 'Leistung:' und bei Bedarf 'Ressourcen:'
        (Format siehe Systemprompt). Auf dieser Ebene ausführlich: 'Leistung:' mit
        Umfang und Abgrenzung ist der wichtigste Text des Plans."""
    )
    arbeitspakete: list[Arbeitspaket] = Field(
        default_factory=list,
        description="""Arbeitspakete. Nur befüllen, wenn der Umfang des Leistungsbereichs
        eine Zwischenebene erfordert. Sonst leer lassen.""",
    )
    aufgaben: list[Aufgabe] = Field(
        default_factory=list,
        description="""Aufgaben direkt unter dem Leistungsbereich. Nur befüllen, wenn
        keine Arbeitspakete verwendet werden. Sonst leer lassen.""",
    )
    # Use sources only on retrieval stage
    sources: list[str] = Field(
        default_factory=list,
        description="""Historische Referenzprojekte (aus den bereitgestellten
        Referenzprojekten), aus denen dieser Leistungsbereich übernommen oder
        abgeleitet wurde. Ein Eintrag pro Projekt im Format 'project_number -
        customer - title', z.B. 'PRJ-1234 - Musterbau GmbH -
        Server-Migration'. Nur mit Angaben aus den bereitgestellten
        Referenzprojekten füllen, nichts erfinden. Leer lassen, wenn kein
        Referenzprojekt maßgeblich beigetragen hat.""",
    )

    @model_validator(mode="after")
    def _check_single_level(self) -> "Leistungsbereich":
        """
        An empty service area stays allowed on purpose. It is a normal step
        while editing, when the user adds a level first and fills it in
        afterwards.
        """
        if self.arbeitspakete and self.aufgaben:
            raise ValueError(
                f"Leistungsbereich '{self.key}': entweder Arbeitspakete oder "
                f"Aufgaben, nicht beides."
            )
        return self


class Wbs(BaseModel):
    """
    The work breakdown structure of one project.
    """
    leistungsbereiche: list[Leistungsbereich] = Field(
        description="""Leistungsbereiche des Projekts"""
    )


def renumber(wbs: Wbs) -> None:
    """
    Give every node a sequential key again, in place.

    Keys carry the position in the structure, so they have to be rebuilt
    after a node was added, deleted or moved (F-02). Tasks below a work
    package get three levels, tasks below a service area only two.
    """
    for lb_number, leistungsbereich in enumerate(wbs.leistungsbereiche, start=1):
        leistungsbereich.key = str(lb_number)

        for ap_number, arbeitspaket in enumerate(leistungsbereich.arbeitspakete, start=1):
            arbeitspaket.key = f"{leistungsbereich.key}.{ap_number}"
            for task_number, aufgabe in enumerate(arbeitspaket.aufgaben, start=1):
                aufgabe.key = f"{arbeitspaket.key}.{task_number}"

        for task_number, aufgabe in enumerate(leistungsbereich.aufgaben, start=1):
            aufgabe.key = f"{leistungsbereich.key}.{task_number}"


def delete_node(siblings: list, index: int) -> None:
    """
    Remove one node from the list it belongs to.
    """
    siblings.pop(index)


def move_node(siblings: list, index: int, offset: int) -> None:
    """
    Move one node up or down among its siblings.

    Offset is -1 to move up and 1 to move down. Moves beyond the first or
    last position are ignored, so the caller does not have to guard the edges.
    """
    target = index + offset
    if 0 <= target < len(siblings):
        siblings.insert(target, siblings.pop(index))
