import streamlit as st
from views.utils.common import submit_message, submit_generation, render_conversation
from views.utils.wbs_tree import render_wbs_tree


def render_wbs_phase() -> None:
    """Render the phase that creates and edits the Wbs."""
    st.subheader(":material/account_tree: Projektstrukturplan")
    tree = st.session_state.wbs
    st.caption(
        st.session_state.project_title if tree
        else "Lass uns nun einen ersten Entwurf für die Projektplanung erstellen."
    )

    with st.expander("Projektbeschreibung anzeigen"):
        st.text_area("Projektbeschreibung", st.session_state.project_description, height=140)

    left, right = st.columns([2, 2], gap="small")
    with left:
        if st.session_state.wbs is None:
            st.info("Noch kein Entwurf vorhanden.")
            if st.button(
                "PSP erstellen",
                icon=":material/auto_awesome:",
                type="primary",
                disabled=not st.session_state.project_description,
            ):
                with st.spinner("Erstelle Projektstrukturplan..."):
                    try:
                        submit_generation()
                        st.rerun()
                    except Exception as error:
                        st.error(f"Error: {error}")
        if st.session_state.wbs is not None:
            with st.container(height=540, border=True):
                render_wbs_tree(st.session_state.wbs)

    with right:
        render_conversation(height=540)

    user_input = st.chat_input("PSP anpassen...", key="wbs_chat_input")
    if user_input:
        submit_message(user_input)
        st.rerun()
