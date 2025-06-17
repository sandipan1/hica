import asyncio
import sys
from .agent import Agent
from .core import Thread, Event
from .state import ThreadStore
from .logging import logger

async def run_cli(agent: Agent, store: ThreadStore):
    if len(sys.argv) < 2:
        logger.error("No message provided")
        print("Error: Please provide a message as a command line argument")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    logger.debug("CLI input received", message=message)
    thread = Thread(events=[Event(type="user_input", data=message)])
    thread_id = store.create(thread)
    new_thread = await agent.agent_loop(thread)
    store.update(thread_id, new_thread)
    last_event = new_thread.events[-1]

    while last_event.data.get("intent") == "request_clarification":
        print(f"{last_event.data['message']}\n> ", end="")
        response = input()
        logger.debug("Human response via CLI", response=response)
        thread.events.append(Event(type="human_response", data=response))
        new_thread = await agent.agent_loop(thread)
        store.update(thread_id, new_thread)
        last_event = new_thread.events[-1]

    final_message = last_event.data.get("message", "")
    logger.info("CLI execution completed", final_message=final_message)
    print(final_message)
    sys.exit(0)