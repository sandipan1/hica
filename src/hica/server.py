from typing import TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import Agent
from .core import Event, Thread
from .logging import logger
from .state import ThreadStore

T = TypeVar("T")


class ThreadRequest(BaseModel):
    message: str


class ResponsePayload(BaseModel):
    type: str = "response"
    response: str


class ApprovalPayload(BaseModel):
    type: str = "approval"
    approved: bool
    comment: str | None = None


Payload = ResponsePayload | ApprovalPayload


def create_app(agent: Agent[T], store: ThreadStore) -> FastAPI:
    app = FastAPI()
    logger.info("FastAPI app created")

    @app.post("/thread")
    async def start_thread(request: ThreadRequest):
        logger.debug("Starting new thread", message=request.message)
        thread = Thread[T](events=[Event(type="user_input", data=request.message)])
        thread_id = store.create(thread)

        new_thread = await agent.agent_loop(thread)
        store.update(thread_id, new_thread)
        last_event = new_thread.events[-1]
        last_event.data["response_url"] = f"/thread/{thread_id}/response"
        logger.info("Thread started", thread_id=thread_id)
        return {"thread_id": thread_id, **new_thread.dict()}

    @app.get("/thread/{thread_id}")
    async def get_thread(thread_id: str):
        thread = store.get(thread_id)
        if not thread:
            logger.warning("Thread not found", thread_id=thread_id)
            raise HTTPException(status_code=404, detail="Thread not found")
        logger.debug("Thread retrieved", thread_id=thread_id)
        return thread

    @app.post("/thread/{thread_id}/response")
    async def handle_response(thread_id: str, payload: Payload):
        thread = store.get(thread_id)
        if not thread:
            logger.warning("Thread not found for response", thread_id=thread_id)
            raise HTTPException(status_code=404, detail="Thread not found")

        last_event = thread.events[-1]
        logger.debug(
            "Handling response", thread_id=thread_id, payload_type=payload.type
        )

        if thread.awaiting_human_response() and payload.type == "response":
            thread.events.append(Event(type="human_response", data=payload.response))
            logger.debug("Human response recorded", response=payload.response)
        elif thread.awaiting_human_approval() and payload.type == "approval":
            if not payload.approved:
                thread.events.append(
                    Event(
                        type="tool_response",
                        data=f"user denied the operation with feedback: {payload.comment or 'none'}",
                    )
                )
                logger.info("Operation denied", comment=payload.comment)
            else:
                # last_event.data should contain intent and arguments
                intent = last_event.data.get("intent")
                arguments = last_event.data.get("arguments", {})
                result = await agent.tool_registry.execute_tool(intent, arguments)
                thread.events.append(Event(type="tool_response", data=result))
                logger.info("Operation approved and executed", result=result)
        else:
            logger.error(
                "Invalid response request",
                payload_type=payload.type,
                awaiting_response=thread.awaiting_human_response(),
                awaiting_approval=thread.awaiting_human_approval(),
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid request: {payload.type}",
                    "awaiting_human_response": thread.awaiting_human_response(),
                    "awaiting_human_approval": thread.awaiting_human_approval(),
                },
            )

        new_thread = await agent.agent_loop(thread)
        store.update(thread_id, new_thread)
        last_event = new_thread.events[-1]
        last_event.data["response_url"] = f"/thread/{thread_id}/response"
        logger.info("Response processed", thread_id=thread_id)
        return new_thread

    return app
