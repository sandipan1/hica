import asyncio
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, model_validator
from rich import print

from hica.agent import Agent, AgentConfig
from hica.core import Thread
from hica.logging import get_thread_logger
from hica.memory import ConversationMemoryStore
from hica.tools import ToolRegistry

load_dotenv()

toolregistry = ToolRegistry()


# Pydantic models for structured output and validation
@toolregistry.tool()
class EmailContact(BaseModel):
    email: str
    domain: str = None  # Will be set after validation

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    @model_validator(mode="after")
    def set_domain(self):
        self.domain = self.email.split("@")[-1]
        return self


class Customer(BaseModel):
    name: str
    contact: EmailContact

    @model_validator(mode="after")
    def validate_name_email_match(self):
        name_part = self.name.lower().split()[0]
        if name_part not in self.contact.email.lower():
            print(f"Warning: Email {self.contact.email} may not match name {self.name}")
        return self


class CustomerList(BaseModel):
    customers: List[Customer]


ALLOWED_DOMAINS = {"example.com", "opensource.org", "abc.com"}


@toolregistry.tool()
async def parse_customers(agent: Agent, raw_text: str) -> List[Customer]:
    res = await agent.run_llm(
        prompt=f"Extract customer information from the following text: {raw_text}",
        response_model=CustomerList,
    )
    return res.customers


@toolregistry.tool()
def validate_domains(customers: List[Customer]) -> Dict[str, List[Dict[str, Any]]]:
    valid = []
    invalid = []
    for c in customers:
        domain = c.contact.domain
        c_dict = c.model_dump()
        if domain in ALLOWED_DOMAINS:
            valid.append(c_dict)
        else:
            c_dict["invalid_reason"] = f"Domain '{domain}' not allowed"
            invalid.append(c_dict)
    return {"valid": valid, "invalid": invalid}


@toolregistry.tool()
async def generate_custom_messages(
    agent: Agent, valid_customers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    drafts = []
    for c in valid_customers:
        draft = await agent.run_llm(
            prompt=f"Write a friendly welcome email to {c['name']} at {c['contact']['email']} to our community around FOSS.",
            response_model=str,
        )
        drafts.append({"customer": c, "draft": draft})
    return drafts


async def main():
    thread = Thread()
    logger = get_thread_logger(thread_id=thread.thread_id)
    store = ConversationMemoryStore(backend_type="file", context_dir="context")

    thread.add_event(
        type="user_input",
        data="Customer 1: John Doe with email john.doe@example.com and  Customer 2: Sandy Hal with email sandy.hald@example.com, Customer 3: Bob Bad with email bob@notallowed.net  ",
    )
    logger.info("add user input")

    store.set(thread=thread)
    agent = Agent(config=AgentConfig(model="openai/gpt-4.1-mini"))
    # Step 1: Parse customers
    customers = await parse_customers(
        agent, thread.events[-1].data
    )  ## thread['user_input']
    thread.add_event(
        type="tool_response",
        step="parse_customers",
        data=[c.model_dump() for c in customers],
    )
    store.set(thread=thread)
    logger.info("extracted customers from user query ")
    # Step 2: Validate domains
    domain_results = validate_domains(customers)
    thread.add_event(type="tool_response", step="validate_domains", data=domain_results)
    store.set(thread=thread)

    # Step 3: Generate welcome emails
    welcome_emails = await generate_custom_messages(agent, domain_results["valid"])
    thread.add_event(type="llm_response", step="welcome_messages", data=welcome_emails)
    store.set(thread=thread)
    logger.info("welcome emails are generated")
    print("\nValid customers and their welcome emails:")
    for item in welcome_emails:
        c = item["customer"]
        print(f"\nTo: {c['name']} <{c['contact']['email']}>\n---\n{item['draft']}")

    print("\nInvalid customers:")
    for item in domain_results["invalid"]:
        print(
            f"{item['name']} <{item['contact']['email']}>: {item.get('invalid_reason', 'Unknown reason')}"
        )
    print(thread.thread_id)


if __name__ == "__main__":
    asyncio.run(main())


### type 1 : you let llm decide - thread conversation decision
## type 2: custom workflow -
## conversation history is your decision

## context
