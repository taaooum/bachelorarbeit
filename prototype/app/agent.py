from dataclasses import dataclass
from typing import Literal
from qdrant_client.models import Filter, FieldCondition, MatchAny
from rag import search_relevant_lessons_learned, search_relevant_work_breakdown_structures
from llm import call_llm_structured
from models.messages import DescriptionResult, ServiceAreaResult, WbsResult
from models.description import Description
from models.wbs import Wbs

# -----------------------------------------------------------------------------
# prompts and constants.

ROLE = """
    Du unterstützt als erfahrener Projektleiter die Angebotsphase eines IT-Beratungsunternehmens.
    Ziel ist eine Kalkulationsgrundlage: ein erster Projektstrukturplan (PSP), den der Nutzer
    versteht und mitgestalten kann. Du arbeitest strukturiert, nachvollziehbar und ohne zu erfinden.
"""

PHASE_PROMPTS = {
    "desc": ROLE + """
        In diesem Schritt entsteht noch kein Plan. Aus Notizen und ersten Gedanken des Nutzers
        erarbeitest du im Gespräch eine kurze, strukturierte Projektbeschreibung. Sie ist später
        die Grundlage für Leistungsbereiche und PSP. Die Notizen können unvollständig oder
        unsortiert sein - du klärst, was fehlt.

        Diese Angaben sprichst du alle an, jede mindestens einmal, in dieser Reihenfolge:
        1. Projektkategorie (z.B. Infrastruktur, Softwareentwicklung, Security)
        2. Kunde, ggf. Branche
        3. Ziel des Projekts für den Kunden
        4. Umfang: Was ist enthalten, was ausdrücklich nicht?
        5. Grober Zeitrahmen (Start, Ende oder Dauer; ungefähre Angaben reichen)
        6. Vorhandene Hardware, Software oder Lizenzen beim Kunden
        7. Sicherheits- oder Compliance-Anforderungen
        8. Anforderungen an Dokumentation
        9. Schulungen für den Kunden
        10. Bekannte Hürden beim Kunden
        11. Weitere Punkte, die dir als Projektleiter für dieses Projekt relevant erscheinen

        Eine Angabe gilt als erledigt, wenn der Nutzer sie beantwortet hat oder sagt, dass er es
        nicht weiß oder es für dieses Projekt nicht relevant ist. Dann nicht nachbohren, sondern
        unter "Offen:" festhalten und zur nächsten Angabe gehen.

        Vorgehen:
        - Höchstens drei Rückfragen pro Nachricht, immer die nächsten offenen Angaben der Liste.
        - Rechne mit kurzen Antworten. Fasse Bekanntes nicht jedes Mal neu zusammen, frage nur nach dem, was fehlt.
        - Erfinde nichts. Was der Nutzer nicht gesagt hat, steht nicht in der Beschreibung.
        - Was der Nutzer nicht weiß oder als nicht relevant bezeichnet, steht als letzter Absatz
          "Offen:" in der Beschreibung.
        - 'ready' erst, wenn alle Angaben der Liste erledigt sind - oder wenn der Nutzer ausdrücklich
          weitermachen will ("weiter", "reicht"); nicht Angesprochenes dann unter "Offen:". Sonst 'continue'.
        - Bei 'ready': kurze Zusammenfassung und der Hinweis, dass die Ansicht zur Planungsphase
          wechselt und der Nutzer dort links auf "PSP erstellen" klickt.
    """,
    "wbs": ROLE + """
        Du erhältst:
        - die Projektbeschreibung (Grundlage des Plans),
        - die aktuelle Struktur (zuletzt gespeicherter Plan, ggf. vom Nutzer per Hand geändert),
        - historische Referenzprojekte je Leistungsbereich aus DocBee,
        - historische Lessons Learned.

        Aufbau des Plans:
        - Gliedere das Projekt auf Basis der Projektbeschreibung in Leistungsbereiche.
        - Eine Zwischenebene aus Arbeitspaketen nur, wenn der Umfang eines Leistungsbereichs das
          erfordert. Ein Leistungsbereich enthält entweder Arbeitspakete oder direkt Aufgaben, nie beides.
        - Wenn Leistungsbereich leer sind und nicht von ihm selber erstellt worden sind, frage den Nutzer ob diese ausgearbeitet werden sollen (mit Aufgaben und ggf. Arbeitspaketen).
        - Fortlaufende Gliederungsnummern ('1', '1.1', '1.1.1').
        - Erfinde keine Angaben, die aus der Projektbeschreibung nicht hervorgehen. Lieber eine offene
          Frage in der 'response' als eine plausible Erfindung.

        Aufbau jeder Beschreibung (Leistungsbereich, Arbeitspaket und Aufgabe gleich):
        - "Aufwand:" - Schätzung in PT mit der Grundlage in Klammern, oder "offen".
        - "Leistung:" - was enthalten ist und was ausdrücklich nicht. Beim Leistungsbereich der
          wichtigste und ausführlichste Teil des Plans, bei Arbeitspaketen und Aufgaben ein Satz
          oder wenige Stichpunkte.
        - "Ressourcen:" - benötigte Hardware, Software oder Lizenzen. Weglassen, wenn nichts anfällt.

        Aufwandsschätzung:
        - Grundlage ist ein Referenzprojekt oder eine konkrete Angabe aus der Projektbeschreibung
          (Anzahl Standorte, Nutzer, Systeme). Die Klammer hinter dem Aufwand nennt, woraus die Zahl
          abgeleitet ist - nicht, aus welchem Projekt, das steht in 'sources'.
        - Referenzen liefern Stunden: 'dokumentiert' ist der Ist-Aufwand und zählt mehr als 'geplant'.
          8 Stunden = 1 PT. Skaliere nachvollziehbar auf das aktuelle Projekt.
        - Der Aufwand einer Ebene ist die Summe der Ebene darunter, sofern dort alle Aufwände bekannt sind.
        - Ohne Grundlage: "Aufwand: offen" schreiben und den Nutzer in der 'response' nach seiner
          Einschätzung fragen. Keine erfundenen Zahlen.
        - Schlage einen Puffer vor, wenn Risiken oder Unsicherheiten erkennbar sind, und weise ihn als solchen aus.

        Änderungswünsche:
        - Existiert eine aktuelle Struktur, ist sie der Ausgangspunkt. Ändere nur, was der Nutzer verlangt
          oder zu einer Lesson Learned bestätigt hat. Alles andere - Titel, Beschreibungen, Aufwände,
          Quellen, manuelle Änderungen des Nutzers - bleibt unverändert. Gib immer die vollständige Struktur zurück.
        - Nummerierung nach Änderungen fortlaufend halten.

        Quellen:
        - 'sources' enthält ausschließlich Referenzprojekte, nie Lessons Learned. Nur eintragen, wenn das
          Referenzprojekt tatsächlich in Struktur oder Aufwand eingeflossen ist.

        Lessons Learned:
        - Es gibt übergreifende und projektspezifische. Prüfe, welche für dieses Projekt wirklich relevant
          sind, und trage nur diese in 'relevant_lessons' ein.
        - Sprich neue relevante Lessons Learned in der 'response' an: kurz, worum es geht, und welchen
          konkreten Vorschlag du für diesen Plan ableitest. Höchstens fünf pro Nachricht, die wichtigsten
          zuerst; weitere in späteren Nachrichten.
        - Ändere den Plan wegen einer Lesson Learned erst, wenn der Nutzer zugestimmt hat. Lessons, zu denen
          der Nutzer sich schon geäußert hat (angenommen oder abgelehnt), gelten als entschieden und werden
          nicht erneut angesprochen.

        'response':
        - Erkläre den Plan bzw. die Änderung kurz und nachvollziehbar, nenne offene Aufwände und Fragen.
          Der Nutzer sieht den Plan daneben als Baum - wiederhole ihn nicht komplett im Text.
    """,
}

OUTLINE_PROMPT = """
    Entwirf aus der Projektbeschreibung eine Grobgliederung: Welche Leistungsbereiche braucht dieses Projekt?

    Diese Übersicht dient als Suchanfrage gegen Leistungsbereiche abgeschlossener Projekte und gegen
    historische Lessons Learned. Nutze deshalb die Fachbegriffe, die auch in einem vergleichbaren
    Projekt oder einer passenden Lesson Learned stehen würden.

    - Je Leistungsbereich ein kurzer Titel und ein bis zwei Sätze, die die betroffenen Systeme,
      Technologien und Tätigkeiten konkret benennen.
    - Noch keine Arbeitspakete, keine Aufgaben, keine Gliederungsnummern, keine Aufwände.
"""

# Below this similarity a hit counts as noise, not as a reference. Measured against the seed data: topical matches land at 0.6 to 0.7, hits from an unrelated topic stay below 0.45.
SCORE_THRESHOLD = 0.5

@dataclass
class AgentStepResult:
    history: list[dict]
    response: str
    next_phase: str
    description: Description | None = None
    wbs: Wbs | None = None


# -----------------------------------------------------------------------------
# helpers.

def _outline_service_areas(
    history: list[dict],
    description_message: dict,
    work_breakdown_structure: Wbs | None,
) -> list[tuple[str, str]]:
    """
    Return the service areas that drive the search, as (title, description).

    The outline call gets only the dialogue and the description, not the
    plan rules of the wbs prompt. Those would contradict the outline prompt
    (numbering, tasks, effort).
    """
    # Reuse the existing work breakdown structure if available
    if work_breakdown_structure is not None:
        return [
            (lb.title, lb.description)
            for lb in work_breakdown_structure.leistungsbereiche
        ]
    # if not call the llm to generate the service_areas
    messages = [
        {"role": "system", "content": OUTLINE_PROMPT},
        description_message,
    ] + history
    service_areas = call_llm_structured(
        messages=messages,
        schema=ServiceAreaResult,
    )
    return [(lb.title, lb.description) for lb in service_areas.leistungsbereiche]


def _format_hours(node: dict) -> str:
    """
    Format planned and documented hours of one reference node.
    """
    planned = node.get("estimated_hours")
    documented = node.get("documented_hours")
    if planned is None and documented is None:
        return ""
    return f" - geplant {planned if planned is not None else '?'} h, dokumentiert {documented if documented is not None else '?'} h"


def _format_reference(payload: dict) -> str:
    """
    Format one reference service area with its children as a readable block.

    Only the fields the model needs are shown. Ids, scores and flags stay
    out, they would only add noise to the prompt.
    """
    lines = [
        f"- [{payload['project_number']}] {payload['title']} (Kunde: {payload['customer']}){_format_hours(payload)}",
        f"  Beschreibung: {payload['description']}",
    ]
    for child in payload.get("children", []):
        lines.append(f"  - {child.get('node_type')}: {child.get('title')}{_format_hours(child)}")
        for task in child.get("children", []):
            lines.append(f"    - {task.get('node_type')}: {task.get('title')}")
    return "\n".join(lines)


def _retrieve_historic_projects(
    service_areas: list[tuple[str, str]],
    reference_cache: dict[str, str],
) -> str:
    """
    Retrieve relevant reference projects for each service area in the service_areas.

    The formatted block per service area is cached by its search text, so a
    service area that did not change between two turns is not searched again.
    """
    references = []
    for title, description in service_areas:
        query = f"{title} {description}"
        if query not in reference_cache:
            hits = search_relevant_work_breakdown_structures(query)
            # Only consider hits that meet the score threshold
            relevant = [
                _format_reference(hit["payload"])
                for hit in hits
                if hit["score"] >= SCORE_THRESHOLD
            ]
            reference_cache[query] = (
                f"Referenzen für Leistungsbereich '{title}':\n"
                + ("\n".join(relevant) if relevant else "Keine passende Referenz gefunden.")
            )
        references.append(reference_cache[query])
    return "\n\n".join(references)

def _retrieve_basic_lessons_learned() -> list[dict]:
    """
    Return the lessons learned that apply to every project, regardless of service area.
    """
    # Lessons learned in these phases apply to every project, not to one service area
    basic_phases = ["Übergreifend", "Angebotsphase"]
    # Create a filter for the basic phases and retrieve
    basic_phase_filter = Filter(
        must=[FieldCondition(key="project_phase", match=MatchAny(any=basic_phases))]
    )
    result = search_relevant_lessons_learned(
        "allgemeine Lessons Learned",
        top_k=50,
        query_filter=basic_phase_filter
    )
    return result


def _retrieve_semantic_lessons_learned(service_areas: list[tuple[str, str]]) -> list[dict]:
    """
    Return the lessons learned that match a service area semantically.
    """
    hits = []
    for title, description in service_areas:
        for hit in search_relevant_lessons_learned(f"{title} {description}", top_k=3):
            if hit["score"] >= SCORE_THRESHOLD:
                hits.append(hit)
    return hits


def _format_lessons_learned(lessons: list[dict]) -> str:
    """
    Format lessons learned as a compact block for the conversation.
    """
    return "\n".join(
        f"- [{lesson['project_number']}] {lesson['title']} ({lesson['project_type']}, {lesson['skill_team']})\n"
        f"  Projektphase: {lesson['project_phase']}\n"
        f"  Problem: {lesson['problem']}\n"
        f"  Lösung: {lesson['solution']}"
        for lesson in lessons
    )


# -----------------------------------------------------------------------------
# agent step function.

def agent_step(
    user_input: str | None,
    history: list[dict],
    phase: Literal["desc", "wbs"],
    project_description: str,
    work_breakdown_structure: Wbs | None,
    shown_lessons: set[str] | None = None,
    reference_cache: dict[str, str] | None = None,
) -> AgentStepResult:
    # point ids of lessons learned already in the history, updated in place
    shown_lessons = shown_lessons if shown_lessons is not None else set()
    # formatted reference blocks per service area, updated in place
    reference_cache = reference_cache if reference_cache is not None else {}

    # user_input is None when the "wbs" phase is triggered automatically
    if user_input is not None:
        history.append({
            "role": "user",
            "content": user_input
        })

    if phase == "desc":
        # The system prompt leads, the dialogue follows
        messages = [{"role": "system", "content": PHASE_PROMPTS[phase]}] + history
        result = call_llm_structured(
            messages = messages,
            schema=DescriptionResult
        )
        history.append({
            "role": "assistant",
            "content": result.response
        })
        return AgentStepResult(
            history=history,
            response=result.response,
            next_phase="wbs" if result.phase_status == "ready" else "desc",
            description=result.description,
            wbs=work_breakdown_structure
        )

    elif phase == "wbs":
        description_message = {
            "role": "system",
            "content": f"Projektbeschreibung:\n{project_description}"
        }

        request_history = history
        if user_input is None:
            request_history = history + [{
                "role": "user",
                "content": "Erstelle den Strukturvorschlag auf Basis der Projektbeschreibung."
            }]

        # Phase 1 - outline the service areas that drive the retrieval
        service_areas = _outline_service_areas(request_history, description_message, work_breakdown_structure)
        current_structure = (
            work_breakdown_structure.model_dump_json()
            if work_breakdown_structure is not None
            else "Noch keine Struktur vorhanden."
        )

        # Phase 2 - retrieve reference projects
        references = _retrieve_historic_projects(service_areas, reference_cache)

        # Phase 3 - retrieve lessons learned not shown before
        new_lessons = []
        retrieved_lessons = _retrieve_semantic_lessons_learned(service_areas)
        # The basic lessons apply to every project, so they are only fetched on the first turn. Afterwards they are all in shown_lessons anyway
        if not shown_lessons:
            retrieved_lessons = _retrieve_basic_lessons_learned() + retrieved_lessons
        
        # filter out already shown lessons
        for hit in retrieved_lessons:
            if hit["id"] not in shown_lessons:
                shown_lessons.add(hit["id"])
                new_lessons.append(hit["payload"])

        # Per-turn context. Only the lessons persist in the history, the rest is rebuilt on every turn
        context = [
            {
                "role": "system",
                "content": f"Aktuelle Struktur:\n{current_structure}"
            },
            {
                "role": "system",
                "content": f"Historische Referenzprojekte aus DocBee, je Leistungsbereich:\n{references}"
            },
        ]
        lessons_message = None
        if new_lessons:
            lessons_message = {
                "role": "system",
                "content": f"Historische Lessons Learned:\n{_format_lessons_learned(new_lessons)}"
            }
            context.append(lessons_message)

        # Phase 4 - generate the plan. The context goes in front of the
        # latest user message, so the user's request stays the last thing
        # the model reads
        system_messages = [
            {"role": "system", "content": PHASE_PROMPTS[phase]},
            description_message,
        ]
        conversation_history = request_history[:-1]
        latest_request = request_history[-1]

        messages = system_messages + conversation_history + context + [latest_request]
        result = call_llm_structured(
            messages = messages,
            schema = WbsResult
        )
        # The lessons stay in the history so later turns know they were shown
        if lessons_message is not None:
            history.append(lessons_message)
        history.append({
            "role": "assistant",
            "content": result.response
        })

        return AgentStepResult(
            history=history,
            response=result.response,
            next_phase="wbs",
            wbs=result.work_breakdown_structure,
        )
    else:
        raise ValueError(f"Unknown phase: {phase}")
