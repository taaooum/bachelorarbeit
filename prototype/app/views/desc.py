import streamlit as st
from views.utils.common import submit_message, render_conversation


def render_desc_phase() -> None:
    """Render the project description phase."""
    st.subheader(":material/account_tree: Projektgrundlage")
    st.caption("Besprechen wir erst, worum es in deinem Projekt gehen soll.")

    st.text_area(
        "Aktuelle Projektbeschreibung",
        value=st.session_state.project_description,
        height=140,
    )

    render_conversation(height=460)

    user_input = st.chat_input("Beschreibung präzisieren...", key="post_desc_input")
    if user_input:
        submit_message(user_input)
        st.rerun()
