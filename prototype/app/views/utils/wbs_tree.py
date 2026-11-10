"""Editable work breakdown structure tree, shared by the wbs and export phases."""
import streamlit as st
import models.wbs as wbs


def node_key(node) -> str:
    """
    Return a widget key that belongs to the node itself.

    The key must not be derived from the node's number: that number changes
    whenever something is moved, deleted or added, and Streamlit would then
    keep showing the value of the widget that used to carry it. The identity
    of the node object stays the same while it is moved around, so it is the
    stable choice.
    """
    return f"n{id(node)}"


def apply_structure_change() -> None:
    """Renumber the tree after a node was added, deleted or moved."""
    wbs.renumber(st.session_state.wbs)


def move_node(siblings: list, index: int, offset: int) -> None:
    """Move a node among its siblings and renumber the tree."""
    wbs.move_node(siblings, index, offset)
    apply_structure_change()


def delete_node(siblings: list, index: int) -> None:
    """Delete a node and renumber the tree."""
    wbs.delete_node(siblings, index)
    apply_structure_change()


def add_node(siblings: list, node_type) -> None:
    """
    Append an empty node of the given type and renumber the tree.

    The new node stays empty. Whether a service area gets work packages or
    tasks below it is the user's decision, not something added here.
    """
    siblings.append(node_type(key="", title="", description=""))
    apply_structure_change()


def indented(indent: int):
    """
    Return a container indented by `indent` steps.

    Streamlit has no nesting for expanders, so an empty placeholder column
    on the left carries the indentation.
    """
    if not indent:
        return st.container()
    _, content = st.columns([indent, 24 - indent], gap=None)
    return content


def render_add_button(
    siblings: list, node_type, label: str, indent: int, key: str
) -> None:
    """Render a full width, single line button that appends a node."""
    with indented(indent):
        st.button(
            label,
            icon=":material/add:",
            key=key,
            width="stretch",
            on_click=add_node,
            args=(siblings, node_type),
        )


def render_node(
    node,
    prefix: str,
    label: str,
    sources: list[str],
    siblings: list,
    index: int,
    indent: int = 0,
) -> None:
    """
    Render one Wbs node as a compact row with its actions.

    The node type and its number stay in the caption, title and actions share
    one line, the description sits below. Field labels are hidden because the
    caption already names the level.
    """
    with indented(indent):
        # gap=None binds the caption to its fields, while the surrounding
        # container keeps a small gap between nodes. Related parts sit close
        # together, separate nodes stay apart.
        with st.container(gap=None):
            st.caption(label)

            title_col, sources_col, order_up, order_down, delete = st.columns(
                [9, 1.2, 1, 1, 1], gap=None
            )
            with title_col:
                st.text_input(
                    "Titel",
                    value=node.title,
                    key=f"{prefix}_title",
                    label_visibility="collapsed",
                    placeholder="Titel",
                )
            with sources_col:
                with st.popover(":material/info:"):
                    if sources:
                        for source in sources:
                            st.markdown(f"- {source}")
                    else:
                        st.markdown("Keine Quellen verfügbar.")
            with order_up:
                st.button(
                    "",
                    icon=":material/keyboard_arrow_up:",
                    key=f"{prefix}_order_up",
                    help="Nach oben",
                    disabled=index == 0,
                    on_click=move_node,
                    args=(siblings, index, -1),
                )
            with order_down:
                st.button(
                    "",
                    icon=":material/keyboard_arrow_down:",
                    key=f"{prefix}_order_down",
                    help="Nach unten",
                    disabled=index == len(siblings) - 1,
                    on_click=move_node,
                    args=(siblings, index, 1),
                )
            with delete:
                st.button(
                    "",
                    icon=":material/delete:",
                    key=f"{prefix}_delete",
                    help="Löschen",
                    on_click=delete_node,
                    args=(siblings, index),
                )
                
            description_height = 140 if indent == 0 else 40
            st.text_area(
                "Beschreibung",
                value=node.description,
                height=description_height,
                key=f"{prefix}_description",
                label_visibility="collapsed",
                placeholder="Beschreibung",
            )


def render_wbs_tree(psp: wbs.Wbs) -> None:
    """
    Render the editable work breakdown structure tree.

    Every service area is one bordered block so its children stay visually
    attached to it. Work packages and tasks are indented inside that block,
    which makes the three levels readable without opening anything.
    """
    for lb_index, lb in enumerate(psp.leistungsbereiche):
        with st.container(border=True, gap="small"):
            render_node(
                lb,
                prefix=node_key(lb),
                label=f":material/folder: **Leistungsbereich {lb.key}**",
                sources=lb.sources,
                siblings=psp.leistungsbereiche,
                index=lb_index,
            )

            for ap_index, ap in enumerate(lb.arbeitspakete):
                render_node(
                    ap,
                    prefix=node_key(ap),
                    label=f":material/list_alt: Arbeitspaket {ap.key}",
                    sources=ap.sources,
                    siblings=lb.arbeitspakete,
                    index=ap_index,
                    indent=1,
                )
                for task_index, auf in enumerate(ap.aufgaben):
                    render_node(
                        auf,
                        prefix=node_key(auf),
                        label=f":material/check_box_outline_blank: Aufgabe {auf.key}",
                        sources=auf.sources,
                        siblings=ap.aufgaben,
                        index=task_index,
                        indent=2,
                    )
                render_add_button(
                    ap.aufgaben,
                    wbs.Aufgabe,
                    "Aufgabe",
                    indent=2,
                    key=f"add_auf_{node_key(ap)}",
                )

            for task_index, auf in enumerate(lb.aufgaben):
                render_node(
                    auf,
                    prefix=node_key(auf),
                    label=f":material/check_box_outline_blank: Aufgabe {auf.key}",
                    sources=auf.sources,
                    siblings=lb.aufgaben,
                    index=task_index,
                    indent=1,
                )
            if not lb.aufgaben:
                render_add_button(
                    lb.arbeitspakete,
                    wbs.Arbeitspaket,
                    "Arbeitspaket",
                    indent=1,
                    key=f"add_ap_{node_key(lb)}",
                )
            if not lb.arbeitspakete:
                render_add_button(
                    lb.aufgaben,
                    wbs.Aufgabe,
                    "Aufgabe",
                    indent=1,
                    key=f"add_auf_{node_key(lb)}",
                )

    render_add_button(
        psp.leistungsbereiche,
        wbs.Leistungsbereich,
        "Leistungsbereich",
        indent=0,
        key="add_lb",
    )
