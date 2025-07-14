import asyncio
import sys

from rich import print

from hica.agent import Agent, AgentConfig
from hica.core import Thread
from hica.logging import get_thread_logger
from hica.memory import ConversationMemoryStore
from hica.tools import MCPConnectionManager, ToolRegistry

# 1. Connect to MCP pubmed server
# mcp_config = {
#     "mcpServers": {"pubmed": {"command": "python", "args": ["-m", "pubmed-mcp-server"]}}
# }
pubmed_mcp = MCPConnectionManager("http://127.0.0.1:8000/mcp/")  # Adjust if needed
registry = ToolRegistry()

agent = Agent(config=AgentConfig(model="openai/gpt-4.1-mini"))


async def main():
    await pubmed_mcp.connect()
    await registry.load_mcp_tools(pubmed_mcp)
    print(registry.get_tool_definitions())
    store = ConversationMemoryStore(backend_type="file", context_dir="context")

    if not len(sys.argv) > 1:
        topic = "fut2 gene and gut health relation"

        # Use LLM to generate 5 relevant queries for the topic
        thread = Thread()
        thread.add_event(
            type="user_input", data=f"Find me most relevant papers for {topic}"
        )
        print(f"------------{thread.thread_id}------------")
        logger = get_thread_logger(thread_id=thread.thread_id)

        context = f"""1. First Generate 2 highly relevant and diverse PubMed search queries for the topic: '{topic} '.
                2. Now for each generated query , use the search_pubmed_advanced tool to find 5 most relevant papers for each generated query."""

        logger.info("search for papers for generated queries using pubmed database")
        async for updated_thread in agent.agent_loop(thread, context):
            store.set(thread)
        if thread.events[-1].data.get("intent") == "clarification":
            print(f"To resume, run: python pubmed_rag.py {thread.thread_id}")

        # # 3. Search 5 most relevant papers for each query (in parallel)
        # async def search_papers(query):
        #     # Assume MCP tool is called 'search_pubmed'
        #     prompt = f"For the query: {query} , search for most revelant papers on pubmed and return top 5"
        #     agent._select_tool(thread=thread)

        # results = await asyncio.gather(*(search_papers(q) for q in queries))

        # # 4. Consolidate name and links
        # consolidated = []
        # for paper_list in results:
        #     for paper in paper_list:
        #         consolidated.append(
        #             {"title": paper.get("title"), "link": paper.get("link")}
        #         )

        # # 5. Save in a file memory store
        # store = FileMemoryStore("pubmed_papers.json")
        # store.set(topic, consolidated)

        # print(
        #     f"Saved {len(consolidated)} papers for topic '{topic}' in pubmed_papers.json:"
        # )
        # for paper in consolidated:
        #     print(f"- {paper['title']} ({paper['link']})")

    else:
        thread_id = sys.argv[1]
        thread = store.get(thread_id)
        if not thread:
            print(f"Thread with id {thread_id} not found.")
            return
        logger = get_thread_logger(thread_id)
        if thread.awaiting_human_response():
            clarification = input(
                f"Enter clarification for :{thread.events[-1].data}   > "
            )
            logger.info(
                "Continuing existing thread from clarification request from user ...",
                clarification,
            )
            thread.add_event(type="user_input", data=clarification)
            async for _ in agent.agent_loop(thread):
                pass
            store.set(thread)

            logger.info(
                "Thread completed",
                events=[e.dict() for e in thread.events],
            )
            if thread.events[-1].data.get("intent") == "clarification":
                print(f"To resume, run: python pubmed_rag.py {thread.thread_id}")
        else:
            print("No clarification needed. Final result:", thread.events[-1].data)
    await pubmed_mcp.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
