import os
import httpx
import logging
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
logger = logging.getLogger(__name__)

async def evaluate_rag_response(question: str, answer: str, context: str) -> dict:
    """
    使用 LLM 评估 RAG 回答质量 (Re-implementation of RAGAS core metrics)
    :param question: 用户问题
    :param answer: 系统回答
    :param context: 检索到的参考上下文
    :return: 评分字典
    """
    prompt = f"""
你是一名严格的 RAG 系统评估员。请根据以下标准对系统的回答进行打分（0.0 - 1.0）：

1. **忠实度 (Faithfulness)**: 回答中的每一条陈述是否都能在【参考上下文】中找到依据？(防止幻觉)
2. **相关性 (Answer Relevancy)**: 回答是否直接、完整地解决了【用户问题】？

【用户问题】
{question}

【参考上下文】
{context[:2000]}... (截断)

【系统回答】
{answer}

请输出 JSON 格式结果：
{{
    "faithfulness_score": 0.0-1.0,
    "relevancy_score": 0.0-1.0,
    "reason": "简要评分理由"
}}
"""
    try:
        import asyncio
        max_retries = 3
        retry_delay = 5  # 秒
        response = None
        
        async with httpx.AsyncClient() as client:
            for retry in range(max_retries):
                try:
                    logger.info(f"发送评估请求到Dashscope API，重试次数: {retry+1}/{max_retries}")
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
                                "result_format": "message"
                            }
                        },
                        timeout=120.0  # 增加超时时间到120秒
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Evaluation API failed: {response.text}")
                        return {"faithfulness_score": 0.0, "relevancy_score": 0.0, "reason": "Evaluator API Error"}

                    logger.info(f"成功收到评估Dashscope API响应")
                    break  # 成功，退出重试循环
                except httpx.TimeoutException:
                    logger.warning(f"评估请求超时，{retry+1}/{max_retries}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有评估请求重试都失败了，请求超时")
                        return {"faithfulness_score": 0.0, "relevancy_score": 0.0, "reason": "Evaluator API Timeout"}
                except httpx.RequestError as e:
                    logger.warning(f"评估请求失败，{retry+1}/{max_retries}，错误: {e}，将在{retry_delay}秒后重试...")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避
                    else:
                        logger.error(f"所有评估请求重试都失败了，错误: {e}")
                        return {"faithfulness_score": 0.0, "relevancy_score": 0.0, "reason": f"Evaluator API Error: {str(e)}"}
        
        data = response.json()
        content = data["output"]["choices"][0]["message"]["content"]
        
        # 尝试提取 JSON
        try:
            # 清理 Markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            logger.warning(f"Evaluator JSON decode failed. Raw output: {content}")
            return {"faithfulness_score": 0.0, "relevancy_score": 0.0, "reason": "Evaluation Format Error"}

    except Exception as e:
        logger.error(f"Auto-evaluation failed: {str(e)}")
        return {"faithfulness_score": 0.0, "relevancy_score": 0.0, "reason": str(e)}
