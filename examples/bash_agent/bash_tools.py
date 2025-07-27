from typing import Any, Dict

from hica import Agent, AgentConfig, Thread, ToolRegistry
from hica.memory import ConversationMemoryStore
from hica.models import ToolResult
from hica.tools import BaseTool, MCPConnectionManager


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


class FileSystemTool(BaseTool):
    """A tool that delegates a filesystem task to a sub-agent that uses MCP tools."""

    name = "run_filesystem_task"
    description = (
        "Delegates a filesystem task to a sub-agent which uses an MCP server to execute it."
    )

    def __init__(self, memory: ConversationMemoryStore):
        self.memory = memory

    async def execute(self, task_description: str) -> ToolResult:
        """
        Delegates a filesystem task to a sub-agent which uses an MCP server to execute it.
        """
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
                result = {
                    "status": "error",
                    "error": "Failed to load any tools from the MCP server.",
                }
                return ToolResult(
                    llm_content=result["error"],
                    display_content=f"❌ **Error:** {result['error']}",
                    raw_result=result,
                )

            sub_agent = FileSystemAgent(tool_registry=sub_agent_registry)
            sub_agent_thread = Thread(metadata={"parent_task": task_description})
            self.memory.set(sub_agent_thread)

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

            result = {
                "status": "success",
                "response": final_response,
                "sub_agent_thread_id": sub_agent_thread.thread_id,
            }
            return ToolResult(
                llm_content=f"File manipulation task completed: {final_response}",
                display_content=f"✅ **Sub-agent Task Finished**\n*Final Message:* {final_response}",
                raw_result=result,
            )
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            return ToolResult(
                llm_content=f"File manipulation task failed: {str(e)}",
                display_content=f"❌ **Error during sub-agent execution:**\n{str(e)}",
                raw_result=result,
            )
        finally:
            await conn.disconnect()