import json
import os
import tempfile
from typing import Dict, List, Optional
from uuid import UUID

from calculator_tools import (
    registry,  # Predefined ToolRegistry
)
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hica import Agent, AgentConfig, ThreadStore
from hica.core import Event, Thread
from hica.logging import get_thread_logger

load_dotenv()

app = FastAPI(title="Agentic Workflow API")


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

# Thread store
store = ThreadStore()


async def process_thread(thread: Thread, thread_id: str, metadata: Dict) -> Thread:
    """Run the agent loop for a thread."""
    logger = get_thread_logger(thread_id, metadata)
    logger.info("Processing thread", user_input=thread.events[-1].data)
    # conn = MCPConnectionManager(
    #     "/Users/sandipan/projects/AI/hica/examples/calculator_mcp_tools.py"
    # )
    agent = Agent(
        config=agent_config,
        tool_registry=registry,  # Use predefined registry
        metadata=metadata,
    )
    updated_thread = await agent.agent_loop(thread)
    store.update(thread_id, updated_thread)
    logger.info(
        "Thread completed",
        events=[e.dict() for e in updated_thread.events],
    )
    return updated_thread


@app.post("/threads", response_model=ThreadResponse)
async def create_thread(request: CreateThreadRequest):
    """Create a new thread with user input."""
    metadata = request.metadata or {"userid": "default", "role": "user"}

    # Create thread
    thread = Thread(
        events=[
            Event(
                type="user_input",
                data=request.user_input,
            )
        ],
        metadata={"user_metadata": metadata},  # Store metadata for reuse
    )
    thread_id = store.create(thread)

    # Process thread
    updated_thread = await process_thread(thread, thread_id, metadata)

    return ThreadResponse(
        thread_id=thread_id,
        events=[e.dict() for e in updated_thread.events],
        status="completed"
        if not updated_thread.awaiting_human_response()
        else "awaiting_response",
        awaiting_human_response=updated_thread.awaiting_human_response(),
    )


@app.post("/threads/{thread_id}/resume", response_model=ThreadResponse)
async def resume_thread(thread_id: UUID, request: ResumeThreadRequest):
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

    # Process thread with original metadata
    metadata = thread.metadata.get("user_metadata", {})
    updated_thread = await process_thread(thread, str(thread_id), metadata)

    return ThreadResponse(
        thread_id=str(thread_id),
        events=[e.dict() for e in updated_thread.events],
        status="completed"
        if not updated_thread.awaiting_human_response()
        else "awaiting_response",
        awaiting_human_response=updated_thread.awaiting_human_response(),
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
async def get_thread_context_file(thread_id: UUID, background_tasks: BackgroundTasks):
    """Download the thread's context as a JSON file."""
    thread = store.get(str(thread_id))
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Prepare context data
    context_data = {
        "thread_id": str(thread_id),
        "events": [e.dict() for e in thread.events],
        "status": "completed"
        if not thread.awaiting_human_response()
        else "awaiting_response",
        "awaiting_human_response": thread.awaiting_human_response(),
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_file:
        json.dump(context_data, temp_file, indent=2)
        temp_file_path = temp_file.name

    # Return file as response
    background_tasks.add_task(os.remove, temp_file_path)
    return FileResponse(
        path=temp_file_path,
        filename=f"context_{str(thread_id)}.json",
        media_type="application/json",
    )


@app.get("/tools")
def list_tools():
    """List all available tools in the calculator registry."""
    tools = []
    for name, tool_def in registry.get_tool_definitions().items():
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


"""
