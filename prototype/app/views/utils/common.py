"""Chat helpers shared by every phase that talks to the agent."""
import time
import streamlit as st
from agent import agent_step


def submit_message(user_input: str) -> None:
    """
    Add a user message to the conversation, get the model's reply, and
    advance to the next phase if agent_step() reports the current one done.

    agent_step() appends both the user prompt and the assistant response to
    messages itself, so no separate append happens here.
    """
    with st.spinner("Verarbeite ..."):
        result = agent_step(
            user_input,
            st.session_state.messages,
            st.session_state.phase,
            st.session_state.project_description,
            st.session_state.wbs,
            st.session_state.lessons_cache,
            st.session_state.reference_cache,
        )
    st.session_state.phase = result.next_phase
    if result.wbs is not None:
        st.session_state.wbs = result.wbs
    if result.description is not None:
        st.session_state.project_title = result.description.title
        st.session_state.project_description = result.description.description


def submit_generation() -> None:
    """
    Trigger the generation of the initial work breakdown structure based on the current project description.
    """
    result = agent_step(
        user_input=None,
        history=st.session_state.messages,
        phase="wbs",
        project_description=st.session_state.project_description,
        work_breakdown_structure=st.session_state.wbs,
        shown_lessons=st.session_state.lessons_cache,
        reference_cache=st.session_state.reference_cache,
    )
    st.session_state.wbs = result.wbs


def render_conversation(height: int = 420) -> None:
    """
    Render the conversation messages in a container.

    System messages stay hidden. They carry context for the model, for
    example the lessons learned candidates, not dialogue for the user.
    """
    def stream_data(data: str):
        for word in data.split(" "):
            yield word + " "
            time.sleep(0.02)

    with st.container(border=True, height=height):
        messages = [
            message for message in st.session_state.messages
            if message["role"] != "system"
        ]
        if not messages:
            return

        for message in messages[:-1]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        last_message = messages[-1]
        with st.chat_message(last_message["role"]):
            if st.session_state.get("_streamed_count", 0) >= len(messages):
                st.write(last_message["content"])
            else:
                st.write_stream(stream_data(last_message["content"]))
                st.session_state["_streamed_count"] = len(messages)
