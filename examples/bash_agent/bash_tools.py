from typing import Any, Dict

from hica import Agent, AgentConfig, Thread, ToolRegistry
from hica.memory import ConversationMemoryStore
from hica.tools import MCPConnectionManager


class FileSystemAgent(Agent):
    """A specialized agent for performing filesystem tasks using MCP tools."""

    def __init__(self, tool_registry: ToolRegistry, **kwargs):
        config = AgentConfig(
            model="openai/gpt-4.1-mini",
            system_prompt=(
                "You are a helpful assistant that uses tools to accomplish filesystem tasks. "
                "Given a task, break it down into steps and use the available tools to execute it."
            ),
        )
        super().__init__(config=config, tool_registry=tool_registry, **kwargs)


class FileSystemSubagentTool:
    """A tool that delegates a filesystem task to a sub-agent that uses MCP tools."""

    def __init__(self, main_agent_thread: Thread, memory: ConversationMemoryStore):
        self.main_agent_thread = main_agent_thread
        self.memory = memory
        # self.mcp_work_dir = os.path.abspath("examples/bash_agent/mcp_work_dir")
        # os.makedirs(self.mcp_work_dir, exist_ok=True)

    async def run_filesystem_task(self, task_description: str) -> Dict[str, Any]:
        """
        Delegates a filesystem task to a sub-agent which uses an MCP server to execute it.
        """
        # The command will be executed from the project root. We `cd` into the workspace
        # so that the MCP server resolves all paths relative to that directory.
        mcp_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "bash",
                    "args": ["-c", "npx -y @modelcontextprotocol/server-filesystem ."],
                }
            }
        }

        conn = MCPConnectionManager(mcp_config)
        sub_agent_registry = ToolRegistry()

        try:
            await conn.connect()
            await sub_agent_registry.load_mcp_tools(conn)

            if not sub_agent_registry.all_tool_defs:
                return {
                    "status": "error",
                    "error": "Failed to load any tools from the MCP server.",
                }

            sub_agent = FileSystemAgent(tool_registry=sub_agent_registry)
            sub_agent_thread = Thread()
            self.memory.set(sub_agent_thread)

            self.main_agent_thread.add_event(
                type="tool_call",
                data={
                    "intent": "run_filesystem_task",
                    "arguments": {"task_description": task_description},
                    "sub_agent_thread_id": sub_agent_thread.thread_id,
                },
            )
            self.memory.set(self.main_agent_thread)

            sub_agent_thread.add_event(type="user_input", data=task_description)
            self.memory.set(sub_agent_thread)

            final_events = []
            async for thread_state in sub_agent.agent_loop(thread=sub_agent_thread):
                self.memory.set(thread_state)
                final_events = thread_state.events

            final_response = "Task completed."
            if final_events and final_events[-1].type == "llm_response":
                if isinstance(final_events[-1].data, dict):
                    final_response = final_events[-1].data.get(
                        "message", final_response
                    )

            return {
                "status": "success",
                "response": final_response,
                "sub_agent_thread_id": sub_agent_thread.thread_id,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            await conn.disconnect()


def get_filesystem_subagent_tool(
    thread: Thread, memory: ConversationMemoryStore
) -> FileSystemSubagentTool:
    """Factory function to create a FileSystemSubagentTool instance."""
    return FileSystemSubagentTool(thread, memory)
