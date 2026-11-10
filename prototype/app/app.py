import streamlit as st
from dataclasses import dataclass
from views.init import render_init_phase
from views.desc import render_desc_phase
from views.wbs import render_wbs_phase
from views.export import render_export_phase
from views.guide import render_guide_phase



# -----------------------------------------------------------------------------
# constants.

@dataclass(frozen=True)
class Phase:
    key: str
    label: str
    icon: str
    visible: bool


PHASES: list[Phase] = [
    Phase("init", "Start", ":material/rocket_launch:", False),
    Phase("guide", "Geführter Einstieg", ":material/checklist:", False),
    Phase("desc", "Beschreiben", ":material/description:", True),
    Phase("wbs", "Planen", ":material/account_tree:", True),
    Phase("export", "Exportieren", ":material/checklist:", True),
]

RENDERERS = {
    "init": render_init_phase,
    "guide": render_guide_phase,
    "desc": render_desc_phase,
    "wbs": render_wbs_phase,
    "export": render_export_phase,
}

VISIBLE_PHASES = [phase for phase in PHASES if phase.visible]

# -----------------------------------------------------------------------------
# helpers.

def init_session_state() -> None:
    st.session_state.setdefault("phase", "init")
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("project_title", "")
    st.session_state.setdefault("project_description", "")
    st.session_state.setdefault("wbs", None)
    st.session_state.setdefault("lessons_cache", set())  # point ids already shown in the chat
    st.session_state.setdefault("reference_cache", {})  # search text -> formatted references
    st.session_state.setdefault("guide_step", 0)
    st.session_state.setdefault("guide_answers", {})  # key -> answer string

def reset_session() -> None:
    for key in ("phase", "messages", "project_title", "project_description", "wbs", "lessons_cache", "reference_cache", "guide_step", "guide_answers"):
        st.session_state.pop(key, None)
    init_session_state()

def current_phase() -> Phase:
    return next(phase for phase in PHASES if phase.key == st.session_state.phase)


def phase_index(key: str) -> int:
    return next(index for index, phase in enumerate(VISIBLE_PHASES) if phase.key == key)


def goto(key: str) -> None:
    st.session_state.phase = key


def is_visible(key: str) -> bool:
    return any(phase.key == key for phase in VISIBLE_PHASES)


def go_next() -> None:
    if not is_visible(st.session_state.phase):
        if VISIBLE_PHASES:
            goto(VISIBLE_PHASES[0].key)
        return

    index = phase_index(st.session_state.phase)
    if index + 1 < len(VISIBLE_PHASES):
        goto(VISIBLE_PHASES[index + 1].key)


def go_previous() -> None:
    index = phase_index(st.session_state.phase)
    if index > 0:
        goto(VISIBLE_PHASES[index - 1].key)


def has_next() -> bool:
    if not is_visible(st.session_state.phase):
        return bool(VISIBLE_PHASES)
    return phase_index(st.session_state.phase) + 1 < len(VISIBLE_PHASES)


def has_previous() -> bool:
    return is_visible(st.session_state.phase) and phase_index(st.session_state.phase) > 0

# -----------------------------------------------------------------------------
# ui.

st.set_page_config(page_title="Projektplaner", page_icon="🔵", layout="wide")
st.logo(":material/token:")

init_session_state()

current = current_phase()
col_space, col_content, col_nav = st.columns([1, 4, 1], gap="medium")

with col_content:
    RENDERERS[current.key]()

with col_nav:
    if current.key != "init":
        st.caption("KI-gestützter Projektplanungsassistent")
        with st.container(horizontal_alignment="center", border=True):
            st.caption("Starte nochmal frisch")
            st.button(
                "Neuer Chat",
                icon=":material/add:",
                width="stretch",
                type="primary",
                on_click=reset_session,
            )
            
            st.divider()
            
            st.caption(":material/format_list_bulleted: Projektphasen")
            for phase in VISIBLE_PHASES:
                is_current = phase.key == current.key
                st.button(
                    phase.label,
                    icon=phase.icon,
                    key=f"nav_{phase.key}",
                    width="stretch",
                    type="primary" if is_current else "tertiary",
                    on_click=goto,
                    args=(phase.key,),
                )

            st.divider()

            nav_col_left, nav_col_right = st.columns(2)
            with nav_col_left:
                st.button(
                    "Zurück",
                    icon=":material/arrow_back:",
                    width="stretch",
                    disabled=not has_previous(),
                    on_click=go_previous,
                )
            with nav_col_right:
                st.button(
                    "Weiter",
                    icon=":material/arrow_forward:",
                    width="stretch",
                    type="primary",
                    disabled=not has_next(),
                    on_click=go_next,
                )
