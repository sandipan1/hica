import asyncio
from typing import List, Union

import instructor
from dotenv import load_dotenv
from fastmcp import Client
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_ai.tools import ToolDefinition
from rich import print

from pydantic_model import create_model_from_tool_schema

load_dotenv()
config = {
    "mcpServers": {
        "sqlite": {
            "command": "uvx",
            "args": ["mcp-server-sqlite", "--db-path", "db.sqlite"],
        }
    }
}


class LLMResponse(BaseModel):
    """final consolidated response from the LLM for the user query"""

    response: str = Field(
        description="The final response to the user's query after tool calls."
    )


client = Client(config)
async_client = instructor.from_openai(AsyncOpenAI())


class FunctionList(BaseModel):
    """A model representing a list of function names."""

    func_names: List[Union[str]]


# class read_query(BaseModel, ctx):
#     name: str
#     description: str
#     query:


async def new_example(user_query: str):
    async with client:
        tools = await client.list_tools()
        # print(tools)
        # res = await client.call_tool("list_tables")
        # print(res)
        pydantic_schema = []
        for tool in tools:
            # print([tool.name for tool in tools])
            tool_def = ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.inputSchema,
            )
            print(tool.name, tool.description, tool.inputSchema)
            createTableParams = create_model_from_tool_schema(
                tool_def
            )  ## this is the pydantic model
            pydantic_schema.append(createTableParams)
        print(pydantic_schema)

        class ToolUse(BaseModel):
            calls: [Union[tuple(pydantic_schema)]]

        try:
            response = await async_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that can call tools in response to user requests
                        Don't make unnecessary function calls.For each tool call, provide the appropriate parameters based on the tool's schema.

                        """,
                    },
                    {"role": "user", "content": f"{user_query}"},
                ],
                temperature=0.0,
                response_model=ToolUse,
            )
            print(response)
        except Exception as e:
            print(f"Error in API call: {str(e)}")
            return None


async def example(user_query: str):
    async with client:
        tools = await client.list_tools()
        res = await client.call_tool("list_tables")
        print(res)
        print([tool.name for tool in tools])
        # > ['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight']
        print(tools[1].inputSchema)
        # >  {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'SQL query to execute'}}, 'required': ['query']}
        try:
            response = await async_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Identify the tools that will help you answer the user's question.
                        Respond with the names of 0, 1 or 2 tools to use. The available tools are
                        {tools}.

                        Don't make unnecessary function calls.
                        """,
                    },
                    {"role": "user", "content": f"{user_query}"},
                ],
                temperature=0.0,
                response_model=FunctionList,
            )
            print(response.func_names)  ## get tools to call based on the user query

            ## format the tools with parameters to call. The parameters are based on the input schema of the tool
            ## and is decided by the LLM
            tool_definitions = []
            for func_name in response.func_names:
                # Find the tool by name
                tool = next((t for t in tools if t.name == func_name), None)
                if tool:
                    print(f"Schema for {func_name}:")
                    print("Input schema:", tool.inputSchema)
                    tool_def = ToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters_json_schema=tool.inputSchema,
                    )
                    # new_tool_schema =create_model_from_tool_schema()
                    tool_definitions.append(tool_def)

                else:
                    print(f"Tool {func_name} not found in tools list.")
            gpt_response = []
            for tool_calls in tool_definitions:
                x = create_model_from_tool_schema(tool_calls)
                print(f"model dump of the tool : {x.model_json_schema()}")
                response1 = await async_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Figure out if the {user_query} has been resolved without the tool call or not.If not, execute the tool call with the right parameters for the {tool_calls.name} tool with description {tool_calls.description}.
                            """,
                        },
                        {"role": "user", "content": f"{gpt_response}"},
                    ],
                    temperature=0.0,
                    response_model=x,
                )
                print(f"LLM response for parameters {tool_calls.name}:")
                print(response1)
                res = None
                if response1 is not None:
                    res = await client.call_tool(
                        tool_calls.name, response1.model_dump()
                    )
                print(res)
                # else:
                #     res = await client.call_tool(
                #         tool_calls.name, response1.model_dump_json()
                #     )
                # print(res)
                # if flag == 1:
                #     break
                gpt_response.append(
                    {
                        "tool_name": tool_calls.name,
                        "parameters": response1.model_dump(),
                        "response": res[0],
                    }
                )

            print(f"all the rensponses : {gpt_response}")
            final_llm_response = await async_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Conolidate all the reponse from the tools calls and give the user appropriate answer to the {user_query}.
                        """,
                    },
                    {"role": "user", "content": f"{gpt_response}"},
                ],
                temperature=0.0,
                response_model=LLMResponse,
            )
            return final_llm_response

        except Exception as e:
            print(f"Error in API call: {str(e)}")
            return None


# async def example1(user_query: str):
#     async with client:
#         tools = await client.list_tools()
#         res = await client.call_tool("list_tables")
#         print(res)
#         print([tool.name for tool in tools])
#         # > ['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight']
#         print(tools[1].inputSchema)
#         # >  {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'SQL query to execute'}}, 'required': ['query']}
#         try:
#             response = await async_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": f"""Identify the tools that will help you answer the user's question.
#                         Respond with the names of 0, 1 or 2 tools to use. The available tools are
#                         {tools}.

#                         Don't make unnecessary function calls.
#                         """,
#                     },
#                     {"role": "user", "content": f"{user_query}"},
#                 ],
#                 temperature=0.0,
#                 response_model=FunctionList,
#             )
#             print(response.func_names)  ## get tools to call based on the user query

#             ## format the tools with parameters to call. The parameters are based on the input schema of the tool
#             ## and is decided by the LLM
#             tool_definitions = []
#             for func_name in response.func_names:
#                 # Find the tool by name
#                 tool = next((t for t in tools if t.name == func_name), None)
#                 if tool:
#                     print(f"Schema for {func_name}:")
#                     print("Input schema:", tool.inputSchema)
#                     tool_def = ToolDefinition(
#                         name=tool.name,
#                         description=tool.description,
#                         parameters_json_schema=tool.inputSchema,
#                     )
#                     # new_tool_schema =create_model_from_tool_schema()
#                     tool_definitions.append(tool_def)

#                 else:
#                     print(f"Tool {func_name} not found in tools list.")
#             gpt_response = []
#             pydantic_parameter_models= [create_model_from_tool_schema(x) for x in tool_definitions]
#             class ToolCalls(BaseModel):
#                 calls: list(Union[*pydantic_parameter_models])


#             response1 = await async_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": f"""Figure out if the {user_query} has been resolved without the tool call or not.If not, execute the tool call with the right parameters for the {tool_calls.name} tool with description {tool_calls.description}.
#                         """,
#                     },
#                     {"role": "user", "content": f"{gpt_response}"},
#                 ],
#                 temperature=0.0,
#                 response_model=ToolCalls,
#                 )
#                 print(f"LLM response for parameters {tool_calls.name}:")
#                 print(response1)
#                 res = None
#                 if response1 is not None:
#                     res = await client.call_tool(
#                         tool_calls.name, response1.model_dump()
#                     )
#                 print(res)
#                 # else:
#                 #     res = await client.call_tool(
#                 #         tool_calls.name, response1.model_dump_json()
#                 #     )
#                 # print(res)
#                 # if flag == 1:
#                 #     break
#                 gpt_response.append(
#                     {
#                         "tool_name": tool_calls.name,
#                         "parameters": response1.model_dump(),
#                         "response": res[0],
#                     }
#                 )

#             print(f"all the rensponses : {gpt_response}")
#             final_llm_response = await async_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": f"""Conolidate all the reponse from the tools calls and give the user appropriate answer to the {user_query}.
#                         """,
#                     },
#                     {"role": "user", "content": f"{gpt_response}"},
#                 ],
#                 temperature=0.0,
#                 response_model=LLMResponse,
#             )
#             return final_llm_response

#         except Exception as e:
#             print(f"Error in API call: {str(e)}")
#             return None


# 1. Model Definitions
class ToolCall(BaseModel):
    """Model for a single tool call with its parameters"""

    name: str
    description: str
    parameters: dict


class ToolCalls(BaseModel):
    """Model for multiple tool calls with validation"""

    calls: List[Union[ToolCall]]

    @field_validator("calls")
    def validate_tool_calls(cls, v, info: ValidationInfo):
        tools: List[ToolDefinition] = info.context["tools"]
        valid_tool_names = [tool.name for tool in tools]
        invalid_names = [call.name for call in v if call.name not in valid_tool_names]

        if invalid_names:
            raise ValueError(
                f"Tools {invalid_names} are not valid. Valid tools are: {valid_tool_names}"
            )

        if len(v) > 4:
            raise ValueError("You can only select at most 4 tools to call")

        return v


# 2. Tool Model Creation
def create_tool_models(tools: List[ToolDefinition]) -> Dict[str, BaseModel]:
    """
    Creates Pydantic models for each tool based on their schemas.

    Args:
        tools: List of tool definitions from the MCP client

    Returns:
        Dictionary mapping tool names to their Pydantic models
    """
    tool_models = {}
    for tool in tools:
        tool_def = ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters_json_schema=tool.inputSchema,
        )
        tool_models[tool.name] = create_model_from_tool_schema(tool_def)
    return tool_models


# 3. Tool Call Generation
async def generate_tool_calls(
    user_query: str, tools: List[ToolDefinition], async_client
) -> ToolCalls:
    """
    Uses the LLM to generate appropriate tool calls based on the user query.

    Args:
        user_query: The user's input query
        tools: List of available tools
        async_client: The OpenAI async client

    Returns:
        ToolCalls object containing the LLM's chosen tool calls
    """
    return await async_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful assistant that can call tools in response to user requests.
                You have access to the following tools:
                
                {[f"- {tool.name}: {tool.description}" for tool in tools]}
                
                Don't make unnecessary function calls. You can select at most 4 tools to call.
                For each tool call, provide the appropriate parameters based on the tool's schema.
                Think if there is any conditional statement for calling the tools.
                """,
            },
            {"role": "user", "content": user_query},
        ],
        temperature=0.0,
        response_model=ToolCalls,
        context={"tools": tools},
    )


# 4. Tool Execution
async def execute_tool_calls(
    tool_calls: ToolCalls, tool_models: Dict[str, BaseModel], client
) -> List[dict]:
    """
    Executes the generated tool calls and collects their responses.

    Args:
        tool_calls: The generated tool calls to execute
        tool_models: Dictionary of tool models
        client: The MCP client

    Returns:
        List of dictionaries containing tool call results
    """
    gpt_response = []
    for tool_call in tool_calls.calls:
        # Get the appropriate model for this tool
        tool_model = tool_models[tool_call.name]

        # Create an instance of the tool model with the parameters
        tool_instance = tool_model(**tool_call.parameters)

        # Execute the tool call
        res = await client.call_tool(
            tool_call.name,
            tool_instance.model_dump(exclude={"name", "description"}),
        )

        gpt_response.append(
            {
                "tool_name": tool_call.name,
                "parameters": tool_call.parameters,
                "response": res[0] if res else None,
            }
        )

    return gpt_response


# 5. Final Response Generation
async def generate_final_response(
    user_query: str, tool_responses: List[dict], async_client
) -> LLMResponse:
    """
    Generates a final consolidated response from the tool call results.

    Args:
        user_query: The original user query
        tool_responses: List of tool call results
        async_client: The OpenAI async client

    Returns:
        LLMResponse containing the final answer
    """
    return await async_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""Consolidate all the responses from the tool calls and give the user an appropriate answer to: {user_query}""",
            },
            {"role": "user", "content": str(tool_responses)},
        ],
        temperature=0.0,
        response_model=LLMResponse,
    )


# 6. Main Function
async def new_example1(user_query: str):
    """
    Main function that orchestrates the entire process of handling a user query.

    Args:
        user_query: The user's input query

    Returns:
        Final LLM response to the user's query
    """
    async with client:
        try:
            # 1. Get available tools
            tools = await client.list_tools()

            # 2. Create tool models
            tool_models = create_tool_models(tools)

            # 3. Generate tool calls
            tool_calls_response = await generate_tool_calls(
                user_query, tools, async_client
            )

            # 4. Execute tool calls
            tool_responses = await execute_tool_calls(
                tool_calls_response, tool_models, client
            )

            # 5. Generate final response
            final_response = await generate_final_response(
                user_query, tool_responses, async_client
            )

            return final_response

        except Exception as e:
            print(f"Error in API call: {str(e)}")
            return None


if __name__ == "__main__":
    tools_called = asyncio.run(
        new_example1(
            "list all the tables and give me schema for each of them.  "
            # "create table for 2 different animal with name and description and describe each of them "
        )
    )
    print(tools_called.response)
    # print(tools_called.response)
