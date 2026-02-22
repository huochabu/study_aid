from models.llm import SimpleLLM
import logging
from utils.qwen_client import call_qwen

# 初始化日志
logger = logging.getLogger(__name__)

class LLMService(SimpleLLM):
    """
    LLM 服务封装，继承自 SimpleLLM，
    添加统一的 chat_completion 方法以适配 Comparison 功能
    """
    def __init__(self):
        super().__init__()

    async def chat_completion(self, messages: list, temperature: float = 0.3) -> str:
        """
        简单的 Chat Completion 封装，目前仅使用 call_qwen
        TODO: 支持完整的 messages 历史和 temperature 参数
        """
        # 提取最后一条用户消息
        user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), "")
        if not user_message:
            return "No content to generate."
            
        logger.info(f"LLMService: Calling Qwen with prompt length {len(user_message)}")
        
        # 使用现有的 call_qwen (目前是同步的，但在 FastAPI 中最好用 async)
        # 既然 call_qwen 内部是同步 requests，我们这里 wrap 一下或者直接用
        # 注意：simple_llm 中有 async_call_qwen 导入但未在 SimpleLLM 类中使用
        # 我们尝试使用 async_call_qwen 如果可用
        from utils.qwen_client import async_call_qwen
        
        response = await async_call_qwen(user_message)
        return response

    async def translate_academic_text(self, text: str) -> str:
        """
        学术文本翻译：将英文翻译成中文，保持学术风格和专业术语的准确性
        """
        from utils.qwen_client import async_call_qwen
        prompt = f"""
你是一个专业的学术翻译助手。请将以下英文文本翻译成中文，要求：

1. 保持学术风格和专业术语的准确性
2. 忠实原文内容，不添加或删减信息
3. 语句通顺，符合中文表达习惯
4. 保留原文的标点符号和格式

请直接输出翻译结果，不要添加任何引言或说明。

原文：
{text}

翻译：
"""
        response = await async_call_qwen(prompt)
        return response

    async def polish_academic_text(self, text: str) -> str:
        """
        学术文本润色：对英文文本进行语法修正和表达优化，提升学术写作质量
        """
        from utils.qwen_client import async_call_qwen
        prompt = f"""
你是一个专业的学术写作润色助手。请对以下英文文本进行润色，要求：

1. 修正语法错误和拼写错误
2. 优化句式结构，提升表达流畅度
3. 保持学术风格和专业术语的准确性
4. 忠实原文内容，不改变原意
5. 保留原文的标点符号和格式

请直接输出润色后的结果，不要添加任何引言或说明。

原文：
{text}

润色后：
"""
        response = await async_call_qwen(prompt)
        return response

# 全局单例
simple_llm = LLMService()
