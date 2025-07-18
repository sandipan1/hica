import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from uuid import UUID

from calculator_tools import (
    registry,  # Predefined ToolRegistry
)
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from rich import print

from hica import Agent, AgentConfig, ConversationMemoryStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger
from hica.tools import MCPConnectionManager, ToolRegistry

load_dotenv()

# --- Globals for shared state ---
# This registry will be populated at startup with both local and MCP tools
# and used by all API requests.
global_registry = ToolRegistry()

mcp_conn: MCPConnectionManager | None = None


# --- Startup and Shutdown Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_conn, global_registry
    mcp_config = {
        "mcpServers": {
            "puppeteer": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            }
        }
    }
    mcp_conn = MCPConnectionManager(mcp_config)
    try:
        print("Connecting to MCP server and loading tools...")
        await mcp_conn.connect()
        await global_registry.load_mcp_tools(mcp_conn)

        # Also load local tools into the same global registry
        for intent, tool_callable in registry.local_tools.items():
            global_registry.tool(intent=intent)(tool_callable)
        print("Tools loaded successfully.")

    except Exception as e:
        print(f"Error during startup: {e}")
        # Depending on the use case, you might want to exit or handle this differently
        pass
    yield
    print("Disconnecting from MCP server...")
    if mcp_conn:
        await mcp_conn.disconnect()
    print("MCP connection closed.")


app = FastAPI(title="Agentic Workflow API", lifespan=lifespan)


# Request and response models
class CreateThreadRequest(BaseModel):
    user_input: str
    metadata: Optional[Dict] = None


class ResumeThreadRequest(BaseModel):
    user_input: str


class ThreadResponse(BaseModel):
    thread_id: str
    events: List[Dict]
    status: str
    awaiting_human_response: bool


# Agent configuration (same as in main.py)
agent_config = AgentConfig(
    model="openai/gpt-4.1-mini",
    system_prompt=(
        "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
        "Analyze the user input, identify the required operation, and determine if clarification is needed."
    ),
    context_format="json",
)

# Conversation memory store (file-based by default, supports MongoDB)
backend_type = os.getenv("HICA_BACKEND_TYPE", "file")
if backend_type == "mongo":
    mongo_uri = os.getenv("HICA_MONGO_URI", "mongodb://localhost:27017")
    mongo_db = os.getenv("HICA_MONGO_DB", "hica")
    mongo_collection = os.getenv("HICA_MONGO_COLLECTION", "threads")
    store = ConversationMemoryStore(
        backend_type="mongo",
        mongo_uri=mongo_uri,
        mongo_db=mongo_db,
        mongo_collection=mongo_collection,
    )
else:
    store = ConversationMemoryStore()


def get_context_dir():
    return getattr(store, "dir_path", None) or getattr(store, "context_dir", None)


async def process_thread(thread: Thread, thread_id: str, metadata: Dict) -> Thread:
    """Run the agent loop for a thread using the global tool registry."""
    logger = get_thread_logger(thread_id, metadata)
    logger.info("Processing thread", user_input=thread.events[-1].data)

    agent = Agent(
        config=agent_config,
        tool_registry=global_registry,  # Use the pre-initialized global registry
        metadata=metadata,
    )
    async for intermediate_thread in agent.agent_loop(thread):
        store.set(intermediate_thread)
        logger.debug(
            "Intermediate state saved",
            event_count=len(intermediate_thread.events),
        )
    logger.info(
        "Thread completed",
        events=[e.dict() for e in thread.events],
    )
    return thread


@app.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: CreateThreadRequest, background_tasks: BackgroundTasks
):
    """
    Create a new thread and start the agent process in the background.
    Returns immediately with the thread_id so the client can start polling.
    """
    metadata = request.metadata or {"userid": "default", "role": "user"}
    thread = Thread(
        events=[Event(type="user_input", data=request.user_input)],
        metadata={"user_metadata": metadata},
    )
    store.set(thread)
    thread_id = thread.thread_id

    # Run the agent loop in the background
    background_tasks.add_task(process_thread, thread, thread_id, metadata)

    return ThreadResponse(
        thread_id=thread_id,
        events=[e.dict() for e in thread.events],
        status="pending",
        awaiting_human_response=thread.awaiting_human_response(),
    )


@app.post("/threads/{thread_id}/resume", response_model=ThreadResponse)
async def resume_thread(
    thread_id: UUID, request: ResumeThreadRequest, background_tasks: BackgroundTasks
):
    """Resume an existing thread with clarification input."""
    thread = store.get(str(thread_id))
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not thread.awaiting_human_response():
        raise HTTPException(
            status_code=400, detail="Thread is not awaiting human response"
        )

    # Initialize logger
    logger = get_thread_logger(str(thread_id))
    clarification_event = Event(type="user_input", data=request.user_input)
    logger.info(
        "Continuing existing thread from clarification request",
        user_input=request.user_input,
    )

    # Append clarification event
    thread.append_event(clarification_event)
    store.set(thread)  # Save the new event immediately

    # Process thread in the background
    metadata = thread.metadata.get("user_metadata", {})
    background_tasks.add_task(process_thread, thread, str(thread_id), metadata)

    return ThreadResponse(
        thread_id=str(thread_id),
        events=[e.dict() for e in thread.events],
        status="pending",
        awaiting_human_response=False,  # Just responded, so not awaiting now
    )


@app.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: UUID):
    """Retrieve thread information."""
    thread = store.get(str(thread_id))
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    return ThreadResponse(
        thread_id=str(thread_id),
        events=[e.dict() for e in thread.events],
        status="completed"
        if not thread.awaiting_human_response()
        else "awaiting_response",
        awaiting_human_response=thread.awaiting_human_response(),
    )


@app.get("/threads/{thread_id}/context-file", response_class=FileResponse)
async def get_thread_context_file(thread_id: UUID):
    """Download the thread's context as a JSON file from disk."""
    context_dir = get_context_dir()
    if not context_dir:
        raise HTTPException(
            status_code=500, detail="Context directory not available for this backend"
        )
    file_path = context_dir / f"{thread_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Context file not found")

    return FileResponse(
        path=str(file_path),
        filename=f"context_{str(thread_id)}.json",
        media_type="application/json",
    )


@app.get("/threads/{thread_id}/events")
async def get_new_events(thread_id: UUID, since: int = 0):
    """Return only new events since a given index."""
    thread = store.get(str(thread_id))
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    events = [e.dict() for e in thread.events[since:]]
    return {"events": events, "total": len(thread.events)}


@app.get("/tools")
def list_tools():
    """List all available tools from the globally loaded registry."""
    tools = []
    for name, tool_def in global_registry.get_tool_definitions().items():
        tools.append({"name": name, "description": tool_def.description or ""})
    return {"tools": tools}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
Create a thread : 

curl -X POST http://localhost:8000/threads \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Calculate 153 minus 3 and then divide the result", "metadata": {"userid": "1234", "role": "analyst"}}'

Resume a thread: 

curl -X POST http://localhost:8000/threads/<thread_id>/resume \
     -H "Content-Type: application/json" \
     -d '{"user_input": "divide by 2"}'

Get thread context: 
curl http://localhost:8000/threads/<thread_id>

List tools: 
curl http://localhost:8000/tools


"""
