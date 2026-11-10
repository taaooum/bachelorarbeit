import streamlit as st
import models.wbs as wbs
from views.utils.wbs_tree import render_wbs_tree


def export_markdown(tree: wbs.Wbs, project_title: str, project_description: str) -> str:
    """
    Export the work breakdown structure as a Markdown string.
    """
    if tree is None:
        return ""

    markdown_lines = [f"# {project_title}\n"]
    markdown_lines.append(project_description + "\n")
    for lb in tree.leistungsbereiche:
        markdown_lines.append(f"## LB {lb.key} {lb.title}\n")
        markdown_lines.append(lb.description + "\n")
        for ap in lb.arbeitspakete:
            markdown_lines.append(f"### AP {ap.key} {ap.title}\n")
            markdown_lines.append(ap.description + "\n")
            for auf in ap.aufgaben:
                markdown_lines.append(f"- A {auf.key} {auf.title}\n")
                markdown_lines.append(auf.description + "\n")
        for auf in lb.aufgaben:
            markdown_lines.append(f"- A {auf.key} {auf.title}\n")
            markdown_lines.append(auf.description + "\n")

    return "\n".join(markdown_lines)


def render_export_phase() -> None:
    """Render the final Wbs review phase."""
    tree = st.session_state.wbs

    st.subheader(":material/account_tree: Review")
    if tree is None:
        st.caption("Noch kein Entwurf vorhanden.")
        return

    with st.container(height=600, border=True):
        with st.container():
            st.text_input(
                "Projektname",
                value=st.session_state.project_title,
                key="export_title",
            )
            st.text_area(
                "Projektbeschreibung",
                value=st.session_state.project_description,
                height=130,
                key="export_description",
            )
        render_wbs_tree(tree)

    st.download_button(
        "Exportieren als Markdown",
        export_markdown(tree, st.session_state.project_title, st.session_state.project_description),
        file_name=f"{st.session_state.project_title}.md",
        mime="text/markdown",
    )
