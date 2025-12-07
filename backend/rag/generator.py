from ..utils.qwen_client import call_qwen

def generate_answer_with_evidence(query, retrieved_docs):
    context_parts = []
    for i, doc in enumerate(retrieved_docs):
        snippet = doc['content']
        source = doc['meta'].get('source', 'unknown')
        page = doc['meta'].get('page', '?')
        context_parts.append(f"[引用{i+1}]（来源：{source} 第{page}页）：{snippet}")

    context = "\n\n".join(context_parts)
    prompt = f"""
    请基于以下引用内容回答问题。每句话必须标注引用编号（如[引用1]）。不要编造信息。
    
    问题：{query}
    
    引用内容：
    {context}
    """

    try:
        answer = call_qwen(prompt)
    except:
        answer = "抱歉，无法生成答案。"

    evidence_list = [
        {
            "id": f"ref_{i+1}",
            "source": doc['meta']['source'],
            "page": doc['meta']['page'],
            "text": doc['content']
        }
        for i, doc in enumerate(retrieved_docs)
    ]

    return {"answer": answer, "evidence": evidence_list}