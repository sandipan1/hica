import pytest

from hica.core import Thread
from hica.memory import ConversationMemoryStore


@pytest.fixture(scope="module")
def mongo_store():
    # Use a test database and collection to avoid polluting production data
    store = ConversationMemoryStore(
        backend_type="mongo",
        mongo_uri="mongodb://localhost:27017",
        mongo_db="hica_test",
        mongo_collection="test_threads",
    )
    yield store
    # Cleanup: Drop the test collection after tests
    store.mongo_store.collection.drop()


def test_mongo_memory_store_set_get_delete(mongo_store):
    # Create a new thread
    thread = Thread()
    thread.add_event(type="user_input", data="Hello, MongoDB world!")

    # Store the thread
    mongo_store.set(thread)

    # Retrieve the thread
    retrieved = mongo_store.get(thread.thread_id)
    assert retrieved is not None
    assert retrieved.thread_id == thread.thread_id
    assert retrieved.events[0].data == "Hello, MongoDB world!"

    # Delete the thread
    mongo_store.delete(thread.thread_id)
    assert mongo_store.get(thread.thread_id) is None
