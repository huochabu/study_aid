def build_knowledge_graph(agent_output: str) -> dict:
    # 简化：从文本中提取实体关系（实际可用 LLM 结构化）
    nodes = []
    edges = []
    if "timeout" in agent_output.lower():
        nodes.append({"id": "err_1", "type": "error", "label": "Connection Timeout"})
        nodes.append({"id": "cause_1", "type": "cause", "label": "Network or Service Down"})
        edges.append({"source": "err_1", "target": "cause_1", "relation": "caused_by"})
    return {"nodes": nodes, "edges": edges}