# knowledge/mindmap_generator.py
import os
import re
import json
import logging
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any

# 加载环境变量
load_dotenv()

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
    从推理步骤中精准提取思维导图文本（核心：只取带层级符号的纯文本）
    :param reasoning_steps: 后端推理阶段返回的原始文本列表
    :return: 纯思维导图树形文本（无多余内容）
    """
    if not isinstance(reasoning_steps, list) or len(reasoning_steps) == 0:
        logger.warning("推理步骤为空，无文本可提取")
        return ""

    # 遍历所有推理步骤，找包含思维导图特征的文本
    mindmap_candidates = []
    for step in reasoning_steps:
        if not isinstance(step, str):
            continue
        
        # 特征1：包含树形层级符号（├──/└──/│）；特征2：包含核心标题（技术内容分析）
        if "技术内容分析" in step and any(char in step for char in ["├──", "└──", "│"]):
            # 预处理：移除代码块标记（```）、多余换行、空白符
            step_clean = re.sub(r'```[\s\S]*?```', '', step)  # 移除```包裹的内容
            step_clean = re.sub(r'\n{3,}', '\n', step_clean)  # 合并多余换行
            mindmap_candidates.append(step_clean)

    if not mindmap_candidates:
        logger.warning("推理步骤中未找到符合特征的思维导图文本")
        return ""

    # 取最长的候选文本（最完整的思维导图）
    raw_mindmap_text = max(mindmap_candidates, key=len)
    logger.info(f"成功从推理步骤提取思维导图文本，长度：{len(raw_mindmap_text)}")

    # 进一步提纯：只保留从"技术内容分析"开始到非树形文本结束的部分
    lines = [line for line in raw_mindmap_text.split('\n') if line.strip()]
    start_idx = -1
    end_idx = len(lines)
    
    # 定位开始行（技术内容分析）
    for i, line in enumerate(lines):
        if line.strip().startswith("技术内容分析"):
            start_idx = i
            break
    
    if start_idx == -1:
        logger.warning("未找到思维导图根节点（技术内容分析）")
        return ""
    
    # 定位结束行（非树形文本）
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        # 非树形文本判定：无层级符号 + 非空
        if line.strip() and not any(char in line for char in ["├──", "└──", "│", "├", "└"]):
            end_idx = i
            break
    
    # 提取纯思维导图文本
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
    # 兜底结构（解析失败时返回）
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

    # 初始化解析器
    root = None
    stack = []  # 栈：(当前节点, 当前缩进长度)
    node_id = 1  # 全局节点ID（保证前端唯一性）

    # 预计算缩进单位（适配任意缩进：2/4/6个空格 + 符号）
    indent_units = []
    for line in lines[1:]:  # 跳过根节点，分析子节点缩进
        prefix = re.match(r'^([\s│├└─]+)', line)
        if prefix:
            indent_units.append(len(prefix.group(1)))
    # 取最小缩进为单位（适配任意缩进格式）
    base_indent = min(indent_units) if indent_units else 4

    # 逐行解析
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 1. 解析根节点（无缩进）
        if not root and len(line) == len(line_stripped):  # 无缩进 = 根节点
            root = {
                "id": "root",
                "topic": line_stripped,
                "children": []
            }
            stack.append((root, 0))  # (节点, 缩进长度)
            logger.info(f"解析根节点：{line_stripped}")
            continue

        if not root:
            continue

        # 2. 解析子节点（有缩进）
        # 提取前缀（缩进+符号）和节点文本
        prefix_match = re.match(r'^([\s│├└─]+)', line)
        if not prefix_match:
            logger.warning(f"跳过非层级行：{line}")
            continue
        
        prefix = prefix_match.group(1)
        topic = line[len(prefix):].strip()
        if not topic:
            continue

        # 计算当前缩进长度（核心：动态适配）
        current_indent = len(prefix)
        # 计算相对层级（当前缩进 / 基础缩进单位）
        current_level = int(current_indent / base_indent)

        # 3. 维护栈结构（找到当前节点的父节点）
        # 弹出栈中缩进 >= 当前缩进的节点（回到父节点层级）
        while stack and stack[-1][1] >= current_indent:
            stack.pop()

        # 4. 创建子节点（带唯一ID）
        parent_node = stack[-1][0] if stack else root
        child_node = {
            "id": f"node-{node_id}",
            "topic": topic,
            "children": []
        }
        node_id += 1

        # 5. 添加到父节点的children中
        parent_node["children"].append(child_node)
        # 压入栈（供后续子节点使用）
        stack.append((child_node, current_indent))

        logger.debug(f"解析节点：层级{current_level} | {topic}（父节点：{parent_node['topic']}）")

    # 兜底：解析失败返回默认结构
    if not root or len(root["children"]) == 0:
        logger.warning("思维导图层级解析失败，返回默认结构")
        return {"root": fallback_root}

    logger.info(f"层级解析完成：根节点下有 {len(root['children'])} 个一级节点")
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
技术内容分析
├── 编译器问题
│   ├── 错误信息
│   │   ├── Unknown compiler(s)
│   │   ├── [winError 2]
│   │   └── unknown language meson
│   ├── 根因推断
│   │   ├── 原因
│   │   │   ├── 编译器未正确安装
│   │   │   ├── 路径设置不正确
│   │   │   └── 语言设置不正确
│   │   └── 解决方法
│   │       ├── 确保编译器已安装
│   │       ├── 配置环境变量
│   │       ├── 检查 Meson 构建文件
│   │       └── 查看完整日志
└── FastAPI 模块未找到
    ├── 错误信息
    │   └── ModuleNotFoundError
    ├── 根因推断
    │   ├── 原因
    │   │   └── FastAPI 未安装
    │   └── 解决方法
    │       ├── 安装 FastAPI 模块
    │       ├── 激活虚拟环境
    │       └── 检查 PYTHONPATH
        一些后置内容...
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