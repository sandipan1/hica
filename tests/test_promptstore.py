import pytest
from hica.memory import PromptStore, InMemoryMemoryStore

# src/hica/test_memory.py


@pytest.fixture
def prompt_store():
    backend = InMemoryMemoryStore()
    return PromptStore(backend=backend)

def test_get_prompt_simple(prompt_store):
    prompt_store.set("hello", "Hello, world!")
    result = prompt_store.get("hello")
    assert result == "Hello, world!"

def test_get_prompt_with_variables(prompt_store):
    prompt_store.set("greet", "Hello, {name}!")
    result = prompt_store.get("greet", name="Alice")
    assert result == "Hello, Alice!"

def test_get_prompt_missing_key_raises(prompt_store):
    with pytest.raises(KeyError):
        prompt_store.get("not_found")