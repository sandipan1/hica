import uuid

from hica.core import Thread
from hica.models import Event


def test_thread_id_uniqueness():
    t1 = Thread()
    t2 = Thread()
    assert t1.thread_id != t2.thread_id, (
        "Each Thread should have a unique thread_id by default."
    )
    assert isinstance(uuid.UUID(t1.thread_id), uuid.UUID)
    assert isinstance(uuid.UUID(t2.thread_id), uuid.UUID)


def test_thread_id_user_supplied():
    custom_id = str(uuid.uuid4())
    t = Thread(thread_id=custom_id)
    assert t.thread_id == custom_id, "User-supplied thread_id should be respected."


def test_events_and_metadata_are_not_shared():
    t1 = Thread()
    t2 = Thread()
    t1.events.append(Event(type="user", data="hi"))
    t1.metadata["foo"] = "bar"
    assert t2.events == [], "Events should not be shared between Thread instances."
    assert t2.metadata == {}, "Metadata should not be shared between Thread instances."
