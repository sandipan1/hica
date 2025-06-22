import time

import requests
import streamlit as st

# API base URL
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "events" not in st.session_state:
    st.session_state.events = []
if "awaiting_human_response" not in st.session_state:
    st.session_state.awaiting_human_response = False
if "status" not in st.session_state:
    st.session_state.status = None
if "tools_list" not in st.session_state:
    st.session_state.tools_list = None

# Set page configuration
st.set_page_config(
    page_title="Agentic Workflow Chat",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_tools():
    """Fetch tools from the API and cache them in the session state."""
    if st.session_state.tools_list is None:
        try:
            response = requests.get(f"{API_BASE_URL}/tools")
            response.raise_for_status()
            st.session_state.tools_list = response.json().get("tools", [])
        except requests.RequestException as e:
            st.session_state.tools_list = []  # Avoid retrying
            st.toast(f"Could not fetch tools: {e}", icon="⚠️")


# Load tools on app startup
load_tools()


# Function to create a new thread and poll for events
def create_thread(user_input, metadata=None):
    try:
        response = requests.post(
            f"{API_BASE_URL}/threads",
            json={
                "user_input": user_input,
                "metadata": metadata or {"userid": "default", "role": "user"},
            },
        )
        response.raise_for_status()
        data = response.json()
        st.session_state.thread_id = data["thread_id"]
        # Immediately show the first event and thread ID
        st.session_state.events = data.get("events", [])
        st.session_state.status = data.get("status", "pending")
        st.rerun()
    except requests.RequestException as e:
        st.error(f"Error creating thread: {e}")


# Function to resume a thread and poll for events
def resume_thread(thread_id, user_input):
    try:
        response = requests.post(
            f"{API_BASE_URL}/threads/{thread_id}/resume",
            json={"user_input": user_input},
        )
        response.raise_for_status()
        data = response.json()
        st.session_state.events = data["events"]
        st.session_state.awaiting_human_response = data["awaiting_human_response"]
        st.session_state.status = data["status"]
        st.success("Thread resumed successfully")

        # Poll for updated events
        poll_events(thread_id)
    except requests.RequestException as e:
        st.error(f"Error resuming thread: {e}")


# Function to poll for updated events
def poll_events(thread_id, max_attempts=10, delay=1):
    # This function is now primarily called via the "Refresh" button
    # or after a resume action. The main real-time feel comes from
    # the create_thread -> rerun flow.
    attempt = 0
    with st.spinner("Agent is working..."):
        while attempt < max_attempts:
            try:
                response = requests.get(f"{API_BASE_URL}/threads/{thread_id}")
                response.raise_for_status()
                data = response.json()
                new_events = data["events"]
                current_event_count = len(st.session_state.get("events", []))

                if len(new_events) > current_event_count:
                    st.session_state.events = new_events
                    st.session_state.awaiting_human_response = data.get(
                        "awaiting_human_response", False
                    )
                    st.session_state.status = data.get("status", "in_progress")
                    st.rerun()  # Refresh the UI with new events

                # Stop polling if the process is complete or needs input
                if data.get("status") == "completed" or data.get(
                    "awaiting_human_response"
                ):
                    st.session_state.status = data.get("status", "completed")
                    st.rerun()
                    break

                time.sleep(delay)
                attempt += 1
            except requests.RequestException:
                st.toast("Failed to get status from server.", icon="⚠️")
                break


# Function to fetch events directly from API
def fetch_thread(thread_id):
    try:
        response = requests.get(f"{API_BASE_URL}/threads/{thread_id}")
        response.raise_for_status()
        data = response.json()
        st.session_state.events = data["events"]
        st.session_state.awaiting_human_response = data["awaiting_human_response"]
        st.session_state.status = data["status"]
        st.success("Thread events loaded successfully")
    except requests.RequestException as e:
        st.error(f"Error fetching thread: {e}")


# Streamlit UI
st.title("Agentic Workflow Chat")

# Sidebar for thread management
with st.sidebar:
    st.header("Thread Management")
    thread_id_input = st.text_input(
        "Enter Thread ID", value=st.session_state.thread_id or ""
    )
    if st.button("Load Thread"):
        if thread_id_input:
            st.session_state.thread_id = thread_id_input
            fetch_thread(thread_id_input)
            # After loading, immediately start polling for live updates
            poll_events(thread_id_input)

    # List all available tools from session state
    st.header("Available Tools")
    if st.session_state.tools_list:
        for tool in st.session_state.tools_list:
            st.markdown(f"- **{tool['name']}**: {tool['description']}")
    else:
        st.write("No tools available or could not fetch.")

# Main content
st.header("Thread Conversation")
if st.session_state.thread_id:
    st.write(f"**Thread ID**: {st.session_state.thread_id}")
    st.write(f"**Status**: {st.session_state.status}")
    st.write(
        f"**Awaiting Response**: {st.session_state.get('awaiting_human_response', False)}"
    )

    # Display all events in a chat-like format
    for event in st.session_state.get("events", []):
        event_type = event.get("type")
        event_data = event.get("data")
        if event_type == "user_input":
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"{event_data}")
        elif event_type in [
            "llm_response",
            "tool_call",
            "tool_response",
            "final_response",
        ]:
            with st.chat_message("assistant", avatar="🤖"):
                # Special handling for image in tool_response
                if (
                    event_type == "tool_response"
                    and isinstance(event_data, dict)
                    and isinstance(event_data.get("response"), dict)
                    and event_data.get("response", {})
                    .get("mime_type", "")
                    .startswith("image/")
                ):
                    import base64

                    response_content = event_data["response"]
                    st.image(
                        base64.b64decode(response_content["data"]),
                        caption=f"Image from tool ({response_content.get('mime_type')})",
                    )
                elif isinstance(event_data, dict):
                    # Always show intent and event type
                    intent = event_data.get("intent", "N/A")
                    # Show message/data if present and not None/empty
                    message = event_data.get("message")
                    # If message is None or empty, show empty string
                    message_str = message if message not in (None, "None") else ""
                    st.markdown(
                        f"""
                        <div style='
                            background-color: rgba(79, 142, 247, 0.08);
                            border-radius: 8px;
                            padding: 10px 16px;
                            margin-bottom: 8px;
                            border-left: 5px solid #4F8EF7;
                        '>
                            <span style='
                                display: inline-block;
                                background: #4F8EF7;
                                color: #fff;
                                border-radius: 4px;
                                padding: 2px 8px;
                                font-size: 0.85em;
                                margin-right: 8px;
                            '>{event_type.upper()}</span>
                            <span style='
                                display: inline-block;
                                background: rgba(79, 142, 247, 0.18);
                                color: #fff;
                                border-radius: 4px;
                                padding: 2px 8px;
                                font-size: 0.85em;
                                margin-right: 8px;
                            '>{intent.upper()}</span>
                            <span style='font-size: 1.05em; margin-left: 8px; color: inherit;'>{message_str}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # Show additional fields if present (excluding intent and message)
                    extra_keys = [
                        k for k in event_data.keys() if k not in ("message", "intent")
                    ]
                    if extra_keys:
                        extra_data = {k: event_data[k] for k in extra_keys}
                        st.json(extra_data)
                else:
                    # For non-dict data, just show as plain text
                    if event_data not in (None, "None"):
                        st.markdown(f"{event_data}")
else:
    st.write("No thread selected. Enter a message to start a new thread.")

# Input form for interaction
st.header("Send a Message")
user_input = st.text_input(
    "Enter your message",
    placeholder="e.g., Calculate 24 multiplied by 2 and the result",
)
if st.button("Send"):
    if user_input:
        if st.session_state.thread_id and st.session_state.awaiting_human_response:
            resume_thread(st.session_state.thread_id, user_input)
        else:
            create_thread(user_input)

# Refresh button
if st.session_state.thread_id:
    if st.button("Refresh"):
        fetch_thread(st.session_state.thread_id)

# Add custom CSS for better styling
st.markdown(
    """
    <style>
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        max-width: 80%;
    }
    .user .stChatMessage {
        background-color: #e6f3ff;
        align-self: flex-start;
    }
    .assistant .stChatMessage {
        background-color: #f0f0f0;
        align-self: flex-end;
    }
    </style>
    """,
    unsafe_allow_html=True,
)