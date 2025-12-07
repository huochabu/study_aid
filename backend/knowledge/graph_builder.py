# knowledge/graph_builder.py
import os
import re
import json
import logging
import httpx
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# 校验阿里云API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请在 .env 文件中配置 DASHSCOPE_API_KEY")

# ✅ 改为异步函数，解决事件循环冲突
async def extract_knowledge_graph_from_text(text: str, doc_type: str = "general") -> dict:
    """
    从文本中提取结构化的知识图谱信息
    返回格式：{"nodes": [{"id": "...", "label": "...", "type": "..."}], "edges": [{"source": "...", "target": "...", "label": "..."}]}
    """
    try:
        # 限制文本长度，避免超出模型上下文
        text = text[:2000]
        
        # 构建Prompt，强化节点ID唯一性和边的准确性
        prompt = f"""
你是一个专业的知识图谱构建专家，请严格按照以下要求处理文本：
1. 提取节点：
   - 节点类型：Category（分类）、Error（错误）、Solution（解决方案）、RootCause（根因）、Info（信息）
   - 每个节点必须包含：id（英文唯一标识，小写+下划线，如"technical_analysis"）、label（中文显示名）、type（节点类型）
   - 节点ID必须唯一，且简洁易懂
2. 提取边：
   - 每条边必须包含：source（源节点id）、target（目标节点id）、label（关系描述，如"包含"、"导致"、"建议"、"属于"）
   - 确保source和target都能精确对应到nodes中的节点id
   - 边要体现逻辑关系，而非简单关联
3. 输出要求：
   - 仅输出JSON格式，不要包含任何解释、代码块标记
   - 至少生成8个节点和6条边，层级清晰，关系明确
   - 优先生成层级关系：Category -> 子分类 -> 具体节点

文档类型：{doc_type}
文本内容：
{text}

示例输出：
{{
    "nodes": [
        {{"id": "technical_analysis", "label": "技术内容分析", "type": "Category"}},
        {{"id": "error_info", "label": "错误信息", "type": "Category"}},
        {{"id": "file_missing", "label": "文件缺失", "type": "RootCause"}},
        {{"id": "error_code_4058", "label": "错误代码-4058", "type": "Error"}},
        {{"id": "check_path", "label": "检查路径", "type": "Solution"}},
        {{"id": "reinit_project", "label": "重新初始化项目", "type": "Solution"}}
    ],
    "edges": [
        {{"source": "technical_analysis", "target": "error_info", "label": "包含"}},
        {{"source": "error_info", "target": "file_missing", "label": "导致"}},
        {{"source": "error_info", "target": "error_code_4058", "label": "包含"}},
        {{"source": "file_missing", "target": "check_path", "label": "建议"}},
        {{"source": "file_missing", "target": "reinit_project", "label": "建议"}}
    ]
}}
        """

        # ✅ 直接在FastAPI的事件循环中调用，不再新建循环
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-max",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                    "parameters": {
                        "temperature": 0.1,
                        "result_format": "json",
                        "top_p": 0.9
                    }
                }
            )
        response.raise_for_status()
        result = response.json()
        
        # 解析返回结果
        output = result.get("output", {})
        kg_content = output.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        # 清理可能的多余字符（如代码块、注释）
        kg_content = re.sub(r'^```json|```$', '', kg_content).strip()
        kg_data = json.loads(kg_content)
        
        # 校验数据格式
        if not isinstance(kg_data.get("nodes"), list) or not isinstance(kg_data.get("edges"), list):
            raise ValueError("知识图谱格式错误：nodes/edges 必须是数组")
        
        # 校验边的source/target有效性
        node_ids = [node["id"] for node in kg_data["nodes"]]
        valid_edges = []
        for edge in kg_data["edges"]:
            if edge.get("source") in node_ids and edge.get("target") in node_ids:
                valid_edges.append(edge)
            else:
                logger.warning(f"无效边：source={edge.get('source')} 或 target={edge.get('target')} 不存在于节点列表")
        
        kg_data["edges"] = valid_edges
        
        # 补充默认值（防止字段缺失）
        for node in kg_data["nodes"]:
            node.setdefault("id", f"node_{uuid.uuid4().hex[:8]}")
            node.setdefault("type", "Category")
            node.setdefault("label", f"未命名节点_{node['id']}")
        
        for edge in kg_data["edges"]:
            edge.setdefault("label", "关联")
        
        logger.info(f"✅ 知识图谱提取成功：节点数={len(kg_data['nodes'])}, 有效边数={len(kg_data['edges'])}")
        return kg_data
    
    except Exception as e:
        logger.error(f"❌ 知识图谱提取失败: {str(e)}", exc_info=True)
        # 错误兜底（保证返回格式正确）
        return {
            "nodes": [
                {"id": "technical_analysis", "label": "技术内容分析", "type": "Category"},
                {"id": "parse_error", "label": "文本解析失败", "type": "Error"},
                {"id": "check_content", "label": "检查文本内容", "type": "Solution"},
                {"id": "check_api", "label": "检查API配置", "type": "Solution"}
            ],
            "edges": [
                {"source": "technical_analysis", "target": "parse_error", "label": "包含"},
                {"source": "parse_error", "target": "check_content", "label": "解决方案"},
                {"source": "parse_error", "target": "check_api", "label": "解决方案"}
            ]
        }