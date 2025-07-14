import pytest
from pymongo import MongoClient


@pytest.fixture(scope="module")
def mongo_client():
    # Connect to local MongoDB (default port)
    client = MongoClient("mongodb://localhost:27017/")
    yield client
    # Cleanup: Drop the test database after tests
    client.drop_database("test_db")
    client.close()


def test_pymongo_insert_and_find(mongo_client):
    db = mongo_client["test_db"]
    collection = db["test_collection"]

    # Insert a document
    doc = {"name": "Alice", "age": 30}
    insert_result = collection.insert_one(doc)
    assert insert_result.acknowledged

    # Find the document
    found = collection.find_one({"name": "Alice"})
    assert found is not None
    assert found["name"] == "Alice"
    assert found["age"] == 30

    # Clean up: remove the document
    collection.delete_one({"_id": found["_id"]})
