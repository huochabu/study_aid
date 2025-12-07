from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

def get_retriever(document_store: InMemoryDocumentStore):
    return InMemoryBM25Retriever(document_store=document_store)