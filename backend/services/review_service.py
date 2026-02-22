import json
import logging
from typing import Dict, Any
from agents.agent_team import simple_llm

logger = logging.getLogger(__name__)

class ReviewService:
    @staticmethod
    async def generate_review(text: str) -> Dict[str, Any]:
        """
        Generates a structured peer review report for the given text.
        Returns JSON with scores, decision, and critique.
        """
        try:
            # Truncate text to fit context window if necessary
            # [UPDATED] Consistent 20,000 char limit as per user request
            truncated_text = text[:20000] 
            
            prompt = f"""
            你是一名世界顶级的AI领域专家/审稿人。
            用户上传了一篇已经发表（或待发表）的学术论文/技术文档。
            请以“第三方独立评审”的视角，对该工作的**质量、贡献和缺陷**进行深度批判性评价。
            
            【文档片段】
            {truncated_text}
            
            【任务要求】
            不要只是总结！要像审稿人一样犀利地指出：
            - 它的核心贡献真的有那么大吗？(Novelty)
            - 它的实验是否足以支撑结论？(Rigor)
            - 它相比同类工具有什么显着优势或劣势？
            
            请输出严格合法的 JSON 格式，包含以下字段：
            {{
                "scores": {{
                    "novelty": <1-10分，整数>,
                    "methodology": <1-10分，整数>,
                    "rigor": <1-10分，严谨性>,
                    "clarity": <1-10分，表达清晰度>,
                    "impact": <1-10分，应用价值>
                }},
                "decision": "Accept" | "Weak Accept" | "Borderline" | "Reject",
                "summary": "<200字以内的总体评价>",
                "strengths": [
                    "<强项1>",
                    "<强项2>"
                ],
                "weaknesses": [
                    "<弱点1>",
                    "<弱点2>"
                ],
                "detailed_critique": "<详细的评审意见，支持 Markdown 格式>"
            }}
            
            请确保评分客观、公正。对于普通的作业或资料，评分应适中；对于真正的学术创新，给高分。
            """
            
            response = await simple_llm.chat_completion([{"role": "user", "content": prompt}])
            
            # Clean up response if it contains markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response.replace("```json", "", 1)
            if clean_response.startswith("```"):
                clean_response = clean_response.replace("```", "", 1)
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            review_data = json.loads(clean_response)
            
            # Calculate overall score
            scores = review_data.get("scores", {})
            total = sum(scores.values())
            average = total / len(scores) if scores else 0
            review_data["overall_score"] = round(average, 1)
            
            return review_data
            
        except Exception as e:
            logger.error(f"Review generation failed: {e}")
            return {
                "error": str(e),
                "scores": {"novelty": 0, "methodology": 0, "rigor": 0, "clarity": 0, "impact": 0},
                "decision": "Error"
            }
