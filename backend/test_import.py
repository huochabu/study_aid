# test_import.py
from haystack.document_stores.in_memory import InMemoryDocumentStore

store = InMemoryDocumentStore()  # ✅ 不传 embedding_dim
print("✅ 成功创建 InMemoryDocumentStore")