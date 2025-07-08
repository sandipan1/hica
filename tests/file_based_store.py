from hica.core import Thread
from hica.memory import ConversationMemoryStore

# Use file-based storage (each thread as a separate file in 'context' directory)
store = ConversationMemoryStore(backend_type="file", context_dir="context")

# Create a new thread (thread_id is auto-generated)
thread = Thread()
thread.add_event(type="user_input", data="Hello, file-based world!")

# Store the thread
store.set(thread)

# Retrieve the thread
retrieved = store.get(thread.thread_id)
print("File-based retrieved thread:", retrieved)


store1 = ConversationMemoryStore(backend_type="file", context_dir="context")
thread1 = Thread()
thread1.add_event(type="user_input", data="Hello, file-based world! 1")
store1.set(thread1)

retrieved1 = store1.get(thread1.thread_id)
print("File-based retrieved thread:", retrieved1)

store2 = ConversationMemoryStore(backend_type="sql", db_path="conversations.db")
thread2 = Thread()
thread2.add_event(type="user_input", data="Hello, sql-based world! 2")
store2.set(thread2)
retrieved2 = store2.get(thread2.thread_id)
print("SQL-based retrieved thread:", retrieved2)
