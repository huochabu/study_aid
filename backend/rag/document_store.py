# rag/document_store.py

from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter
from haystack import Pipeline

# ✅ 创建 document store：不要传 embedding_dim！
# InMemoryDocumentStore 会自动处理嵌入维度
document_store = InMemoryDocumentStore(embedding_similarity_function="cosine")  # 可选：设为 cosine 更适合中文

# 🔁 注意：索引（indexing）和搜索（search）需要不同的 embedder！
# - indexing 用 DocumentEmbedder（处理 Document 对象）
# - search 用 TextEmbedder（处理字符串查询）

doc_embedder = SentenceTransformersDocumentEmbedder(model="BAAI/bge-small-zh-v1.5")
text_embedder = SentenceTransformersTextEmbedder(model="BAAI/bge-small-zh-v1.5")

retriever = InMemoryEmbeddingRetriever(document_store=document_store)

# ✅ 索引 pipeline：文档 → 嵌入 → 写入
indexing_pipeline = Pipeline()
indexing_pipeline.add_component("embedder", doc_embedder)
indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store))
indexing_pipeline.connect("embedder", "writer")  # 自动连接 documents 输出到 writer

# ✅ 搜索 pipeline：文本 → 嵌入 → 检索
search_pipeline = Pipeline()
search_pipeline.add_component("embedder", text_embedder)
search_pipeline.add_component("retriever", retriever)
search_pipeline.connect("embedder.embedding", "retriever.query_embedding")  # 显式连接嵌入向量