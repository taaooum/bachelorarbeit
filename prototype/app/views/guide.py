from dataclasses import dataclass
import streamlit as st
from views.utils.common import submit_message


@dataclass(frozen=True)
class GuideElem:
    key: str
    question: str
    options: list[str] | None = None


# Flat list of standard questions, asked in order. Every question always has
# a text field; one with options additionally gets clickable pills above it.
# TODO: Add to thesis - for future usage add different sets of questions per project type.
ELEMENTS: list[GuideElem] = [
    GuideElem("kunde", "Für wen ist das Projekt/Wie heißt der Kunde?"),
    GuideElem("produkt", "Welches unserer Produkte/Dienstleistungen wird verkauft?"),
    GuideElem("zeit", "Bis wann soll das Projekt abgeschlossen sein?"),
    GuideElem("ziel", "Was ist das Ziel des Projekts?"),
    GuideElem("hardware", "Welche Hardware ist bekannt und gegen was soll sie eingesetzt werden?"),
    GuideElem("software", "Welche Software und Lizenzen sind relevant?"),
    GuideElem("sicherheit", "Gibt es Sicherheits- oder Compliance-Anforderungen?", ["Keine bekannt", "ISO 27001", "DSGVO-relevant", "Kundenvorgabe"]),
    GuideElem("doku", "Ist eine Dokumentation erforderlich?", ["Nein", "Übergabedoku", "Betriebshandbuch"]),
    GuideElem("schulung", "Sind Schulungen einzuplanen?", ["Nein", "Admins", "Endanwender"]),
    GuideElem("umfang", "Was ist im Projektumfang enthalten?", ["Beschaffung", "Installation", "Migration", "Betrieb"]),
    GuideElem("huerden", "Gibt es bekannte Hürden beim Kunden?", ["Altsysteme", "Verfügbarkeit", "Freigabeprozesse", "Netzwerkrestriktionen"]),
    GuideElem("sonstiges", "Gibt es sonstige relevante Informationen?"),
]


# -----------------------------------------------------------------------------
# helpers.

def _widget_key(elem: GuideElem, suffix: str) -> str:
    return f"guide_{elem.key}{suffix}"


def _read_widget(elem: GuideElem) -> str | None:
    """
    Read the answer for one element: selected pills plus typed text.

    Returns None when nothing was entered, so a skipped and an empty answer
    look the same to build_prompt().
    """
    selected = (st.session_state.get(_widget_key(elem, "_pills")) or []) if elem.options else []
    text = (st.session_state.get(_widget_key(elem, "_text")) or "").strip()
    parts = list(selected) + ([text] if text else [])
    return ", ".join(parts) if parts else None


def _store_and_next(elem: GuideElem) -> None:
    answer = _read_widget(elem)
    if answer is None:
        st.session_state.guide_answers.pop(elem.key, None)
    else:
        st.session_state.guide_answers[elem.key] = answer
    st.session_state.guide_step += 1


def _back() -> None:
    st.session_state.guide_step = max(0, st.session_state.guide_step - 1)


def _build_prompt(answers: dict) -> str:
    """
    Build the first user message of the description phase from the answers.

    Answered questions go in as question plus answer. Skipped ones are listed
    as still open, so the model asks only about those (F-06).
    """
    lines = []
    open_questions = []
    for elem in ELEMENTS:
        answer = answers.get(elem.key)
        if answer:
            lines.append(f"{elem.question} {answer}")
        else:
            open_questions.append(elem.question)
    if open_questions:
        lines.append("Noch nicht angegeben: " + " ".join(open_questions))
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# render.

def _render_question(elem: GuideElem) -> None:
    """
    Render the widget(s) for one element, prefilled from a stored answer.

    The stored answer is one comma-joined string.
    """
    previous = st.session_state.guide_answers.get(elem.key, "")
    parts = previous.split(", ") if previous else []
    st.markdown(f"**{elem.question}**")

    if elem.options:
        selected = [option for option in parts if option in elem.options]
        st.pills(
            elem.question,
            options=elem.options,
            selection_mode="multi",
            default=selected,
            key=_widget_key(elem, "_pills"),
            label_visibility="collapsed",
        )
        remaining = ", ".join(part for part in parts if part not in elem.options)
    else:
        remaining = previous

    st.text_area(
        elem.question,
        value=remaining,
        key=_widget_key(elem, "_text"),
        height=100,
        label_visibility="collapsed",
        placeholder="Antwort ...",
    )


def _render_answers_so_far() -> None:
    answers = st.session_state.guide_answers
    answered = [elem for elem in ELEMENTS if answers.get(elem.key)]
    if not answered:
        return
    with st.expander(f"Bisherige Antworten ({len(answered)})"):
        for elem in answered:
            st.markdown(f"**{elem.question}**  \n{answers[elem.key]}")


def render_guide_phase() -> None:
    """Render the guided start, one question per step."""
    st.subheader(":material/checklist: Geführter Einstieg")
    st.caption(
        "Ich führe dich durch die Standardfragen. Jede Frage kannst du "
        "überspringen - was offen bleibt, klären wir danach im Gespräch."
    )

    step = min(st.session_state.guide_step, len(ELEMENTS) - 1)
    elem = ELEMENTS[step]
    is_last = step == len(ELEMENTS) - 1

    st.progress((step + 1) / len(ELEMENTS), text=f"Frage {step + 1} von {len(ELEMENTS)}")

    with st.container(border=True):
        _render_question(elem)

    finish = False
    with st.container(horizontal=True):
        st.button(
            "Zurück",
            icon=":material/arrow_back:",
            disabled=step == 0,
            on_click=_back,
        )
        if not is_last:
            st.button(
                "Weiter",
                icon=":material/arrow_forward:",
                type="primary",
                on_click=_store_and_next,
                args=(elem,),
            )
        else:
            # No callback here: finishing calls the model, which needs the
            # spinner and a rerun from the main script.
            if st.button("Abschließen", icon=":material/check:", type="primary"):
                answer = _read_widget(elem)
                if answer is not None:
                    st.session_state.guide_answers[elem.key] = answer
                finish = True

    _render_answers_so_far()

    if finish:
        message = _build_prompt(st.session_state.guide_answers)
        st.session_state.phase = "desc"
        try:
            submit_message(message)
        except Exception as error:
            st.session_state.phase = "guide"
            messages = st.session_state.messages
            if messages and messages[-1].get("role") == "user":
                messages.pop()
            st.error(
                "Das Sprachmodell ist gerade nicht erreichbar."
            )
            with st.expander("Details"):
                st.code(str(error)[:600])
            return
        st.rerun()
