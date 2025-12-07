# backend/rag/rag_pipeline.py
from haystack import Pipeline
from haystack.components.retrievers import InMemoryEmbeddingRetriever
from haystack.components.builders import PromptBuilder
from haystack.components.generators import LlamaGenerator  # 或使用 QwenGenerator
from haystack.utils import Secret
import numpy as np

# 注意：你需要先安装支持 Qwen 的组件，比如通过 HuggingFace 或自定义
# 这里以通用方式模拟调用 Qwen API

def run_rag_query(question: str, context: List[str]):
    # Step 1: 向量化问题并检索最相关的上下文
    retriever = InMemoryEmbeddingRetriever(
        embedding_model="bge-small-zh",  # BGE 中文模型
        top_k=3,
    )

    # 构建检索器（假设已加载向量数据）
    # 我们需要一个内存中的向量数据库（见下一步）
    # 先简化处理：直接返回前3个文本块作为context
    relevant_context = context[:3]  # 模拟检索结果

    # Step 2: 构造提示词
    prompt_template = """
    你是专业的技术文档助手。
    请根据以下上下文回答问题，不要编造信息。

    上下文:
    {context}

    问题:
    {question}

    回答:
    """

    prompt_builder = PromptBuilder(template=prompt_template)

    # Step 3: 调用 Qwen 大模型生成答案
    # 使用 Qwen API 示例（需替换为实际 key）
    from qwen_api import call_qwen  # 自定义函数，稍后提供

    full_prompt = prompt_builder.run(context="\n".join(relevant_context), question=question)["prompt"]
    answer = call_qwen(full_prompt)

    return answer