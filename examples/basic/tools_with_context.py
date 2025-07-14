"""
Imagine you are calling different tools . Tool calls are decided based on
1. Tool name and description
2. User context

Say you have a GMAIL tool and CONTACTS tool -
The CONTACTS tool finds email address from name, designation -> LLM crafts a message to the recipient -> Sends the GMAIL

Now if instead of writing a generic mail with generic tone , you can add context for that specific person which helps you draft a
customized message
"""

import asyncio

from hica.agent import Agent, AgentConfig
from hica.core import Thread
from hica.logging import get_thread_logger
from hica.memory import ConversationMemoryStore
from hica.tools import ToolRegistry

# Define the tools
registry = ToolRegistry()


@registry.tool("CONTACTS")
def find_email(name: str, designation: str) -> str:
    """Finds the email address for a person given their name and designation."""
    # Dummy implementation
    if name == "Alice Smith":
        return "alice.smith@company.com"
    return f"{name.lower().replace(' ', '.')}@example.com"


@registry.tool("GMAIL")
def send_email(to: str, subject: str, body: str) -> str:
    """Sends an email to the specified address."""
    # Dummy implementation
    return f"Email sent to {to} with subject '{subject}' and body: {body}"


async def main():
    # User context for personalization
    person_context = "Alice Smith is the Head of Research at CompanyX. She values concise, data-driven communication and appreciates a friendly but professional tone."

    config = AgentConfig(
        system_prompt="You are an assistant that can use CONTACTS to find email addresses and GMAIL to send emails. Use any provided context to personalize your message."
    )
    agent = Agent(config=config, tool_registry=registry)
    thread = Thread()
    store = ConversationMemoryStore(backend_type="file")
    logger = get_thread_logger(thread_id=thread.thread_id)
    logger.info("starting thread..")
    # User asks to send a mail
    thread.add_event(
        type="user_input",
        data="Send a project update to Alice Smith, Head of Research at CompanyX.",
    )

    # Run the agent loop, passing the context for personalization
    async for updated_thread in agent.agent_loop(thread, context=person_context):
        print("Current thread events:")
        for event in updated_thread.events:
            print(event)
    store.set(thread)
    logger.info("----end thread-----")


if __name__ == "__main__":
    asyncio.run(main())
