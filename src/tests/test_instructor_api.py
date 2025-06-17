import instructor
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel


# Configure a dummy client for testing
# In a real scenario, you'd use your actual API key
@pytest.fixture
def instructor_client():
    return instructor.from_openai(AsyncOpenAI())


@pytest.mark.asyncio
async def test_instructor_text_message(instructor_client):
    """Test a simple text message with instructor."""

    class SimpleResponse(BaseModel):
        answer: str

    try:
        response = await instructor_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using a common model for basic testing
            response_model=SimpleResponse,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what is your name?"},
            ],
            temperature=0.0,
        )
        assert isinstance(response.answer, str)
        print(f"Test Simple Text Message: {response.answer}")
    except Exception as e:
        pytest.fail(f"Simple text message test failed: {e}")


@pytest.mark.asyncio
async def test_instructor_structured_message_error(instructor_client):
    """Simulate the error: passing a dict as content without type."""

    class ErrorResponse(BaseModel):
        result: str

    # This is designed to reproduce the 'Missing required parameter' error
    # if the API treats this as a multi-modal message without a specified type.
    structured_data = {"key": "value", "data_type": "example"}

    try:
        response = await instructor_client.chat.completions.create(
            model="gpt-4o",  # This model is more likely to interpret structured content
            response_model=ErrorResponse,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": structured_data},  # PROBLEMATIC LINE
            ],
            temperature=0.0,
        )
        pytest.fail("Expected BadRequestError but got success.")
    except instructor.exceptions.InstructorRetryException as e:
        # Check if the error message matches the expected one
        print(f"Caught expected error: {e}")
        assert "Missing required parameter: 'messages[1].content[0].type'." in str(e)
    except Exception as e:
        pytest.fail(f"Expected InstructorRetryException, but got different error: {e}")


@pytest.mark.asyncio
async def test_instructor_correct_structured_message(instructor_client):
    """Test passing a structured message content correctly (if applicable)."""
    # This part depends on if you intend to send multi-modal messages.
    # If thread.events[-1].data can genuinely be a complex object and you want the LLM to process it as such,
    # you need to format it according to OpenAI's multi-modal message structure.
    # For example, for text and image:
    # content = [
    #     {"type": "text", "text": "What is in this image?"},
    #     {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
    # ]
    # For now, we will test with a simple string converted from a dict to avoid the original error.

    class StructuredResponse(BaseModel):
        analysis: str

    # Simulating a dict being converted to string, which should prevent the error
    user_input_dict = {
        "user_query": "analyze this data",
        "data": {"temp": 25, "humidity": 60},
    }
    user_content_str = str(user_input_dict)

    try:
        response = await instructor_client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=StructuredResponse,
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": user_content_str},  # String content
            ],
            temperature=0.0,
        )
        assert isinstance(response.analysis, str)
        print(f"Test Correct Structured Message (as string): {response.analysis}")
    except Exception as e:
        pytest.fail(f"Correct structured message test failed: {e}")
