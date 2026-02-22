# knowledge/graph_builder.py
import os
import re
import json
import logging
import httpx
import uuid
from dotenv import load_dotenv

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# 加载根目录的.env文件
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
logger = logging.getLogger(__name__)

# 校验阿里云API Key（可选，仅用于知识图谱功能）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    logger.warning("未配置 DASHSCOPE_API_KEY，知识图谱功能将不可用，但学习系统功能仍然可用")

# ✅ 改为异步函数，解决事件循环冲突
async def extract_knowledge_graph_from_text(text: str, doc_type: str = "general") -> dict:
    """
    从文本中提取结构化的知识图谱信息
    返回格式：{"nodes": [{"id": "...", "label": "...", "type": "..."}], "edges": [{"source": "...", "target": "...", "label": "..."}]}
    """
    # 检查是否配置了DASHSCOPE_API_KEY
    if not DASHSCOPE_API_KEY:
        logger.warning("未配置 DASHSCOPE_API_KEY，跳过知识图谱提取")
        return {
            "nodes": [
                {"id": "root", "label": "知识图谱", "type": "Category"},
                {"id": "api_error", "label": "需要API密钥", "type": "Error"},
                {"id": "config_guide", "label": "配置DASHSCOPE_API_KEY", "type": "Solution"}
            ],
            "edges": [
                {"source": "root", "target": "api_error", "label": "包含"},
                {"source": "api_error", "target": "config_guide", "label": "解决方案"}
            ]
        }
    
    try:
        # 限制文本长度，避免超出模型上下文 (增加到10000，解决文本不全导致提取失败)
        text = text[:10000]
        
        # 定义不同场景的 Prompt 模板
        prompts = {
            "academic": """
你是一个学术知识图谱构建专家。请从论文/学术文本中提取核心概念和理论网络：
1. 提取节点：
   - 节点类型：Concept（核心概念）、Theory（理论假设）、Method（方法/算法）、Metric（评估指标）、Result（实验结果）
   - ID要求：尽量使用英文概念名（如 "attention_mechanism"），若无英文则使用中文拼音或简写，需全局唯一。
   - label要求：必须是具体的概念名称（如"注意力机制"），严禁使用"未命名节点"、"节点1"等无意义名称。
2. 提取边：
   - 关系类型：is_part_of（属于）、improves（改进）、evaluates（评估）、proposes（提出）
3. 输出要求：
   - 仅输出JSON，无需Markdown标记。
   - 至少8个节点，6条边。
            """,
            "book": """
你是一个文学/书籍知识图谱专家。请梳理书籍的人物关系和情节脉络：
1. 提取节点：
   - 节点类型：Character（人物）、Event（关键事件）、Location（地点）、Theme（主题）、Chapter（章节）
   - ID要求：英文小写+下划线
   - label要求：必须是具体的人物名、地名或事件名，严禁使用泛代词。
2. 提取边：
   - 关系类型：interacts_with（互动）、happens_at（发生于）、belongs_to（属于）、participates_in（参与）
3. 输出要求：
   - 仅输出JSON，无需Markdown标记。
   - 至少8个节点，6条边。
            """,
            "general": """
你是一个专业的知识图谱构建专家，请从文本中提取核心实体和关系，构建直观的知识图谱：
1. 提取节点：
   - 节点类型：根据内容动态定义（如：Technology, Component, Issue, Solution, Concept 等）。不要局限于固定的死板类型。
   - id：使用英文或拼音作为唯一标识（如 "fastapi_error", "multi_agent_rag"）。
   - label：**必须是具体的中文名称或专有名词**（如"FastAPI模块"、"多智能体RAG"、"内存溢出"）。**严禁**使用"未命名节点"、"Node_1"或过于泛泛的词（如"错误"、"问题"）。
   - 描述力：节点名称应能独立表达含义。
2. 提取边：
   - source/target：对应节点的 id。
   - label：描述两个节点之间的关系（如"导致"、"包含"、"依赖"、"解决"）。
   - 关系要具体：例如 "FastAPI" --[缺少]--> "模块"。
3. 输出要求：
   - 仅输出纯 JSON 格式。
   - 节点数量适中（8-15个），重点突出核心逻辑链。
   - 保证图谱连通性，避免大量孤立节点。
            """
        }

        # 根据 doc_type 选择 Prompt，默认使用 general
        selected_prompt_template = prompts.get(doc_type, prompts["general"])

        # 动态调整请求大小，确保不超过模型限制
        max_request_size = 30720
        initial_truncated_text = text[:10000]  # 初始截断
        final_payload = None
        
        while True:
            # 添加截断提示
            if len(text) > len(initial_truncated_text):
                truncated_text = initial_truncated_text + "\n\n（文本过长，已截断）"
            else:
                truncated_text = initial_truncated_text
            
            # 构建最终 Prompt
            prompt = f"""
{selected_prompt_template}

文档类型：{doc_type}
文本内容：
{truncated_text}
            """
            
            # 构建请求payload
            payload = {
                "model": "qwen-max",
                "input": {"messages": [{"role": "user", "content": prompt}]},
                "parameters": {
                    "temperature": 0.2,
                    "result_format": "json",
                    "top_p": 0.8
                }
            }
            
            # 计算实际的JSON请求大小
            import json
            request_size = len(json.dumps(payload))
            logger.info(f"Knowledge graph request size: {request_size}/{max_request_size} chars")
            
            # 如果请求大小合适，保存最终payload并退出循环
            if request_size <= max_request_size:
                final_payload = payload
                break
            
            # 如果请求大小超过限制，进一步截断
            initial_truncated_text = initial_truncated_text[:int(len(initial_truncated_text) * 0.9)]  # 每次减少10%
            
            # 防止无限循环
            if len(initial_truncated_text) < 1000:
                logger.warning("文本已极度截断，可能影响知识图谱生成效果")
                final_payload = payload
                break
        
        logger.info(f"最终知识图谱请求大小: {len(json.dumps(final_payload))}/{max_request_size} chars")

        # ✅ 直接在FastAPI的事件循环中调用，不再新建循环，添加重试机制
        import asyncio
        max_retries = 3
        retry_delay = 5  # 秒
        response = None
        
        async with httpx.AsyncClient() as client:
            for retry in range(max_retries):
                try:
                    logger.info(f"发送知识图谱请求到Dashscope API，重试次数: {retry+1}/{max_retries}")
                    response = await client.post(
                        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                        headers={
                            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json=final_payload,
                        timeout=120.0  # 增加超时时间到120秒
                    )
                    # 处理响应
                    response.raise_for_status()
                    logger.info(f"成功收到知识图谱Dashscope API响应")
                    break  # 成功，退出重试循环
                except httpx.TimeoutException:
                    logger.warning(f"知识图谱请求超时，{retry+1}/{max_retries}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有知识图谱请求重试都失败了，请求超时")
                        raise
                except httpx.RequestError as e:
                    logger.warning(f"知识图谱请求失败，{retry+1}/{max_retries}，错误: {e}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有知识图谱请求重试都失败了，错误: {e}")
                        raise
        
        result = response.json()
        
        # 解析返回结果
        output = result.get("output", {})
        kg_content = output.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        # 清理可能的多余字符（如代码块、注释）
        # Robust extraction: Prioritize code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', kg_content, re.DOTALL)
        if json_match:
            kg_content = json_match.group(1)
        else:
            # Fallback: find the first '{' and the last '}'
            match_start = kg_content.find('{')
            match_end = kg_content.rfind('}')
            
            if match_start != -1 and match_end != -1 and match_end > match_start:
                kg_content = kg_content[match_start : match_end + 1]
            else:
                 # Fallback cleanup if no braces found (unlikely for JSON, but safe fallback)
                kg_content = re.sub(r'^```json|```$', '', kg_content).strip()

        try:
            kg_data = json.loads(kg_content)
        except json.JSONDecodeError:
             # Last ditch effort: sometimes single quotes are used
             # But standard LLM output with prompts usually respects structure.
             # If fail, try to unescape? No, keep simple.
             logger.error(f"JSON Parsing failed for content: {kg_content[:200]}...")
             raise
        
        # 校验数据格式
        if not isinstance(kg_data.get("nodes"), list) or not isinstance(kg_data.get("edges"), list):
            raise ValueError("知识图谱格式错误：nodes/edges 必须是数组")
        
        # 校验边的source/target有效性
        node_ids = set()
        for node in kg_data["nodes"]:
             # 强制修正：如果label为空，用id代替；
             if not node.get("label"):
                 node["label"] = node.get("id", "未知节点")
             
             # 确保ID存在
             if not node.get("id"):
                 # 基于label生成id
                 node["id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, node["label"]))
             
             node_ids.add(node["id"])

        valid_edges = []
        for edge in kg_data["edges"]:
            s, t = edge.get("source"), edge.get("target")
            if s in node_ids and t in node_ids:
                if not edge.get("label"):
                    edge["label"] = "关联"
                valid_edges.append(edge)
            else:
                logger.warning(f"剔除无效边：{s} -> {t}")
        
        kg_data["edges"] = valid_edges
        
        # 补充默认值（防止字段缺失）
        for node in kg_data["nodes"]:
            node.setdefault("type", "Concept")
        
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