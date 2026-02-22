# knowledge/mindmap_generator.py
import os
import re
import json
import logging
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# 加载根目录的.env文件
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# 配置日志（便于调试推理文本接收/解析过程）
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 校验阿里云API Key（仅备用，优先解析推理文本）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    logger.warning("未配置DASHSCOPE_API_KEY，仅能解析推理阶段的思维导图文本，无法兜底生成")

# ======================
# 步骤1：精准接收推理阶段的文本
# ======================
def extract_mindmap_text_from_reasoning(reasoning_steps: List[str]) -> str:
    """
    从推理步骤中精准提取思维导图文本（核心：只取带层级符号的纯文本或Markdown列表）
    :param reasoning_steps: 后端推理阶段返回的原始文本列表
    :return: 纯思维导图树形文本（无多余内容）
    """
    if not isinstance(reasoning_steps, list) or len(reasoning_steps) == 0:
        logger.warning("推理步骤为空，无文本可提取")
        return ""

    # Strategy 1: Look for explicit header "### 树形思维导图文本描述"
    for step in reasoning_steps:
        if not isinstance(step, str):
            continue
            
        if "### 树形思维导图文本描述" in step:
            logger.info("找到明确的 '树形思维导图文本描述' 标题")
            parts = step.split("### 树形思维导图文本描述")
            if len(parts) > 1:
                content_after = parts[1]
                
                # Simple extraction: split by newlines, take lines that look like list items
                lines = content_after.split('\n')
                mindmap_lines = []
                started = False
                in_code_block = False
                
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                        
                    if stripped.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                        
                    if stripped.startswith("#"): # Next section header
                        # If we already found list items, stop.
                        # If we haven't found any yet, ignore (maybe some intermediate header?)
                        if started: 
                             break 
                        continue 
                    
                    # Check for list item (- or * or +)
                    if re.match(r'^[\s]*[-*+]\s+', line):
                        started = True
                        mindmap_lines.append(line)
                    elif started:
                        # If we already started, and encounter a non-list line:
                        # If it has indentation, it might be a multiline content (we accept it as note)
                        # If it has NO indentation, it effectively ends the list.
                        if not re.match(r'^[\s]', line):
                             break
                        mindmap_lines.append(line)
                
                if mindmap_lines:
                    text = "\n".join(mindmap_lines)
                    logger.info(f"成功通过标题提取思维导图文本，长度：{len(text)}")
                    return text

    # Strategy 2: Look for ASCII Tree or Markdown List candidates
    mindmap_candidates = []
    for step in reasoning_steps:
        if not isinstance(step, str):
            continue
        
        # Check for ASCII tree chars
        has_tree_chars = any(char in step for char in ["├──", "└──", "│"])
        
        # Check for Markdown list structure (at least 3 lines starting with - or *)
        lines = step.split('\n')
        # Count lines that look like list items
        list_item_count = sum(1 for l in lines if re.match(r'^\s*[-*+]\s+', l))
        has_markdown_list = list_item_count >= 3
        
        if has_tree_chars or has_markdown_list:
            # Clean up code blocks tokens but keep content
            # Remove ```markdown or ```
            step_clean = re.sub(r'```\w*\n?', '', step)
            step_clean = re.sub(r'```', '', step_clean)
            step_clean = re.sub(r'\n{3,}', '\n', step_clean)
            mindmap_candidates.append(step_clean)

    if not mindmap_candidates:
        logger.warning("推理步骤中未找到符合特征的思维导图文本")
        return ""

    # Pick the longest candidate
    raw_mindmap_text = max(mindmap_candidates, key=len)
    logger.info(f"成功从推理步骤提取思维导图文本，长度：{len(raw_mindmap_text)}")

    # Refine extraction (trim surrounding text)
    lines = [line for line in raw_mindmap_text.split('\n') if line.strip()]
    
    # Try to find the first line that looks like a tree node or list item
    first_tree_idx = -1
    for i, line in enumerate(lines):
        # ASCII tree or Markdown List Item
        if any(char in line for char in ["├──", "└──", "│"]) or re.match(r'^\s*[-*+]\s+', line):
            first_tree_idx = i
            break
            
    if first_tree_idx == -1:
        return raw_mindmap_text

    # Backtrack to find potential root (headline before the list)
    start_idx = first_tree_idx
    for i in range(first_tree_idx - 1, -1, -1):
        line = lines[i].strip()
        if not line or line.startswith("---") or line.startswith("==="):
            break
        if line.startswith("#"): # Header
            start_idx = i 
            break
        # Also include immediately preceding text line as prompt/root
        start_idx = i 

    end_idx = len(lines)
    pure_mindmap_lines = lines[start_idx:end_idx]
    pure_mindmap_text = "\n".join(pure_mindmap_lines).strip()
    
    logger.debug(f"提纯后的思维导图文本：\n{pure_mindmap_text}")
    return pure_mindmap_text

# ======================
# 步骤2：解析层级结构（适配任意缩进的树形文本）
# ======================
def parse_mindmap_hierarchy(raw_text: str) -> Dict[str, Any]:
    """
    解析树形文本为前端可渲染的层级JSON（核心：动态计算缩进层级）
    :param raw_text: 提纯后的思维导图树形文本
    :return: 带层级的JSON结构（root + children + id）
    """
    fallback_root = {
        "id": "root",
        "topic": "技术内容分析",
        "children": []
    }

    if not raw_text:
        return {"root": fallback_root}

    lines = [line.rstrip('\n') for line in raw_text.split('\n') if line.strip()]
    if not lines:
        return {"root": fallback_root}

    root = None
    stack = []
    node_id = 1
    
    # 预计算缩进单位
    indent_units = []
    pattern_prefix = r'^([\s│├└─\-*+]+)'
    
    for line in lines[1:]:
        prefix = re.match(pattern_prefix, line)
        if prefix:
            indent_units.append(len(prefix.group(1)))
    
    base_indent = min(indent_units) if indent_units else 2 

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if not root:
             # Skip markdown headers before finding real content
             if line_stripped.startswith("###") or line_stripped.startswith("==="):
                 continue

             root_topic = line_stripped
             # Remove leading chars if any
             root_topic = re.sub(r'^[-*+]\s+', '', root_topic)
             
             # If root topic is still empty or looks like a separator, skip
             if not root_topic or root_topic.startswith("---"):
                 continue

             root = {
                "id": "root",
                "topic": root_topic,
                "children": []
             }
             
             root_prefix = re.match(pattern_prefix, line)
             root_indent = len(root_prefix.group(1)) if root_prefix else 0
             
             stack.append((root, root_indent))
             logger.info(f"解析根节点：{root_topic}")
             continue

        # 2. 解析子节点
        prefix_match = re.match(pattern_prefix, line)
        if not prefix_match:
            # 非层级行，作为 note
            if stack:
                last_node = stack[-1][0]
                if "notes" not in last_node:
                    last_node["notes"] = ""
                last_node["notes"] += "\n" + line.strip()
            continue
        
        prefix = prefix_match.group(1)
        topic = line[len(prefix):].strip()
        if not topic:
            continue

        current_indent = len(prefix)
        # 3. 维护栈结构（找到当前节点的父节点）
        # 弹出栈中缩进 >= 当前缩进的节点（回到父节点层级）
        while stack and stack[-1][1] >= current_indent:
            stack.pop()
            
        if not stack:
             parent_node = root
             # Fallback to root as parent if stack is empty
             stack.append((root, -1))
        
        parent_node = stack[-1][0]

        child_node = {
            "id": f"node-{node_id}",
            "topic": topic,
            "children": [],
            "notes": ""
        }
        node_id += 1

        parent_node["children"].append(child_node)
        stack.append((child_node, current_indent))

    if not root:
        return {"root": fallback_root}

    return {"root": root}

# ======================
# 步骤3：主函数（接收推理文本 → 解析 → 输出给前端）
# ======================
async def generate_mindmap_from_kg(kg_dict: dict, reasoning_steps: List[str]) -> Dict[str, Any]:
    """
    前端调用的主函数：
    1. 接收推理阶段的reasoning_steps
    2. 提取纯思维导图文本
    3. 解析为层级JSON
    4. 兜底：解析失败时基于知识图谱生成（可选）
    """
    try:
        # 核心逻辑：优先解析推理阶段的文本
        # 步骤1：提取推理阶段的思维导图文本
        mindmap_raw_text = extract_mindmap_text_from_reasoning(reasoning_steps)
        
        # 步骤2：解析为层级结构
        if mindmap_raw_text:
            mindmap_struct = parse_mindmap_hierarchy(mindmap_raw_text)
            return mindmap_struct

        # 兜底逻辑：推理文本解析失败时，基于知识图谱生成（可选）
        logger.info("推理文本解析失败，基于知识图谱兜底生成")
        if not DASHSCOPE_API_KEY:
            logger.error("无API Key，无法兜底生成")
            return {"root": {"id": "root", "topic": "技术内容分析", "children": []}}

        # 格式化知识图谱为描述文本
        node_desc = []
        for node in kg_dict.get("nodes", []):
            node_desc.append(f"- {node['label']}（类型：{node.get('type', '默认')}）")
        
        edge_desc = []
        for edge in kg_dict.get("edges", []):
            source_label = next((n['label'] for n in kg_dict.get("nodes", []) if n['id'] == edge['source']), edge['source'])
            target_label = next((n['label'] for n in kg_dict.get("nodes", []) if n['id'] == edge['target']), edge['target'])
            edge_desc.append(f"- {source_label} {edge.get('label', '关联')} {target_label}")

        # 构建生成Prompt（强制层级结构）
        prompt = f"""
请将以下知识图谱转换为层级化思维导图JSON，严格遵守：
1. 纯JSON输出，无多余内容；
2. 根节点id为root，topic为"技术内容分析"；
3. 至少3级层级，每个节点带唯一id（格式：node-数字）；
4. 保持层级结构清晰，适配前端树形渲染。

知识图谱节点：
{chr(10).join(node_desc)}

知识图谱关系：
{chr(10).join(edge_desc)}

示例输出：
{{
  "root": {{
    "id": "root",
    "topic": "技术内容分析",
    "children": [
      {{
        "id": "node-1",
        "topic": "一级节点",
        "children": [
          {{"id": "node-2", "topic": "二级节点", "children": [{{"id": "node-3", "topic": "三级节点"}}]}}
        ]
      }}
    ]
  }}
}}
        """

        # 调用阿里云API生成
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

        # 解析生成结果
        output = result.get("output", {})
        mindmap_content = output.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        mindmap_content = re.sub(r'^```json|```$', '', mindmap_content).strip()
        mindmap_data = json.loads(mindmap_content)

        # 校验并补充必要字段
        if "root" not in mindmap_data:
            mindmap_data["root"] = {"id": "root", "topic": "技术内容分析", "children": []}
        mindmap_data["root"].setdefault("id", "root")
        mindmap_data["root"].setdefault("topic", "技术内容分析")
        if not isinstance(mindmap_data["root"].get("children"), list):
            mindmap_data["root"]["children"] = []

        return mindmap_data

    except Exception as e:
        logger.error(f"思维导图生成/解析失败：{str(e)}", exc_info=True)
        # 最终兜底：保证前端有数据可渲染
        return {
            "root": {
                "id": "root",
                "topic": "技术内容分析",
                "children": [
                    {
                        "id": "node-1",
                        "topic": "核心问题",
                        "children": [{"id": "node-2", "topic": "推理文本解析失败，请检查日志"}]
                    }
                ]
            }
        }

# ======================
# 测试入口（验证逻辑，可删除）
# ======================
if __name__ == "__main__":
    import asyncio

    # 模拟推理阶段返回的文本（和你实际的reasoning_steps格式一致）
    mock_reasoning_steps = [
        "一些前置分析内容...",
        """
        ### 树形思维导图文本描述
        - 项目简介
          - 目标与范围
            - 目标
              - 开发基于Multi-Agent RAG技术的多模态运维知识中枢系统
        """,
        "一些后续分析内容..."
    ]

    # 测试：提取 + 解析 流程
    def test_extract_and_parse():
        # 步骤1：提取纯思维导图文本
        raw_text = extract_mindmap_text_from_reasoning(mock_reasoning_steps)
        logger.info(f"提取的纯文本：\n{raw_text}")

        # 步骤2：解析层级结构
        mindmap_struct = parse_mindmap_hierarchy(raw_text)
        logger.info(f"解析后的JSON结构：\n{json.dumps(mindmap_struct, ensure_ascii=False, indent=2)}")

    # 测试主函数
    async def test_main_function():
        mock_kg = {"nodes": [], "edges": []}
        mindmap = await generate_mindmap_from_kg(mock_kg, mock_reasoning_steps)
        logger.info(f"主函数输出：\n{json.dumps(mindmap, ensure_ascii=False, indent=2)}")

    # 运行测试
    test_extract_and_parse()
    asyncio.run(test_main_function())