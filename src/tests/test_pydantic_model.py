# Suppose you want to call the 'add' tool
import asyncio

import instructor
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.tools import ToolDefinition

load_dotenv()

from reference.pydantic_model import create_model_from_tool_schema

# 1. Get the tool definition (you may need to adapt this for your registry)
tool_def = ToolDefinition(
    name="add",
    description="Add two numbers.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"},
        },
        "required": ["a", "b"],
    },
)

# 2. Build the Pydantic model
AddParamsModel = create_model_from_tool_schema(tool_def)
# 3. Use as response_model in LLM call
async_client = instructor.from_openai(AsyncOpenAI())


async def test_pydantic_model():
    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Call the add tool with the right parameters.",
            },
            {"role": "user", "content": "Add 3 and 4."},
        ],
        temperature=0.0,
        response_model=AddParamsModel,
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(test_pydantic_model())

# Now response.a and response.b will be present!
