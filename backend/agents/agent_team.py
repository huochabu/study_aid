# agents/agent_team.py
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import asyncio
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
except Exception:
    pass
import os
from dotenv import load_dotenv

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

import logging
import re
from services.llm import simple_llm

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    logger.warning("未配置 DASHSCOPE_API_KEY，Agent功能将不可用，但学习系统功能仍然可用")
    # 为了让代码能够继续执行，设置一个默认值
    DASHSCOPE_API_KEY = ""

llm_config = {
    "config_list": [{
        "model": "qwen-max",
        "api_key": DASHSCOPE_API_KEY,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "price": [0.004, 0.012] # [FIX] Add dummy price to silence "Model not found" warning

    }],
    "temperature": 0.7,
    # 限制每个Agent的最大回复令牌数
    "max_tokens": 2000,
}

async def simple_extract_keywords(text, top_k=3):
    """
    Use LLM to extract search keywords for better accuracy.
    Falls back to heuristics if LLM fails.
    """
    try:
        # [RESTORED] User requested 20,000 char limit.
        # This balances deep context with performance.
        preview = text[:20000]

        prompt = f"""Extract 3-5 technical keywords/phrases from this text for search and analytics.
        Format: Comma separated list. No numbering.
        Text: {preview}"""
        
        response = await simple_llm.chat_completion([{"role": "user", "content": prompt}])
        if response and "Error" not in response:
            # Clean response
            keywords = [k.strip() for k in response.split(',') if k.strip()]
            if keywords:
                return keywords[:top_k]
    except Exception as e:
        logger.error(f"LLM keyword extraction failed: {e}")

    # Fallback to simple heuristic
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return []
    
    potential_title = lines[0]
    clean_title = re.sub(r'[^\w\s]', '', potential_title)
    words = clean_title.split()
    return words[:top_k]

def create_agents():
    """工厂函数：每次创建新 Agent 实例，避免状态污染"""
    log_expert = AssistantAgent(
        name="日志专家",
        system_message="你是一名日志分析专家。请从日志中提取错误、IP、时间，并推断根因。",
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    config_expert = AssistantAgent(
        name="配置专家",
        system_message="你擅长从技术文档中抽取参数、依赖关系，构建结构化配置知识。",
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    explainer = AssistantAgent(
        name="解释专家",
        system_message="""你负责整合其他专家的输出，生成清晰、结构化的总结。
        
        你的输出必须包含以下固定章节：
        ### 1. 深度分析总结
        (这里是对全文的详细逻辑总结)
        
        ### 树形思维导图文本描述
        (这里使用 Markdown 列表形式输出逻辑结构，前端将据此生成思维导图)
        
        注意：在所有内容输出完毕后，必须另起一行输出：TERMINATE""",
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    paper_expert = AssistantAgent(
        name="学术阅读专家",
        system_message="""你是一名尽职的学术助理。你的任务是提取论文的核心信息，供后续专家使用。
        请用**简洁的学术语言**列出以下要点（严禁长篇大论）：
        1. **创新点 (Novelty)**：一句话概括核心贡献。
        2. **方法论 (Methodology)**：简述核心算法/架构。
        3. **实验结果 (Results)**：列出关键指标(SOTA对比)。
        
        【严重警告】
        ❌ **严禁**输出 "思维导图"、"知识图谱" 或 "核心关键词" 章节。
        ❌ 你的任务仅仅是提供**素材**，总结和绘图工作完全由后续的解释专家完成。
        ❌ 保持客观简洁，不要进行过度解读。""",
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    general_expert = AssistantAgent(
        name="通用知识专家",
        system_message="""你是一名博学的读书顾问。请对书籍/长文本进行深度阅读：
        1. 分章摘要 (Chapter Summary)：按逻辑段落总结核心内容。
        2. 概念提取 (Key Concepts)：识别并解释文中的核心概念（如术语、理论）。
        3. 逻辑梳理 (Logical Flow)：梳理作者的论证逻辑或叙事线索。""",
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    critic = AssistantAgent(
        name="质检员",
        system_message="""你是一名友好的内容检查员。
        
        你的任务是确保专家输出了核心内容（如创新点、方法等），而**不必**过于纠结细节或深度。
        除非内容完全离题或空白，否则请尽量**放行**。

        【检查标准】
        - 是否有基本的内容输出？
        - 格式是否大致清晰？
        
        【输出规则】
        - 只要不是严重错误，请直接回复："APPROVE"。
        - 如果确实缺失核心内容，请用一句话指出。
        """,
        llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config=False
    )

    user_proxy = UserProxyAgent(
        name="用户代理",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),
        code_execution_config={"use_docker": False}
    )
    return user_proxy, log_expert, config_expert, explainer, paper_expert, general_expert, critic



class StreamingGroupChat(GroupChat):
    def __init__(self, agents, messages, max_round=10, speaker_selection_method="auto", allow_repeat_speaker=True, callback=None):
        super().__init__(agents, messages, max_round, speaker_selection_method, allow_repeat_speaker)
        self.callback = callback
        self.explainer_has_spoken = False 

    def _get_agent_by_name(self, name):
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def select_speaker(self, last_speaker, selector):
        """Extremely aggressive speaker selection and termination."""
        
        # [NUCLEAR OPTION] Scan entire message history for ANY message from Explainer
        # This is the most robust way to ensure we never speak twice.
        explainer_detected = False
        for msg in self.messages:
            if "解释" in str(msg.get("name", "")):
                explainer_detected = True
                break
        
        # Also check current flags and last speaker
        should_terminate = (
            explainer_detected or 
            self.explainer_has_spoken or 
            "解释" in last_speaker.name
        )
        
        # Content based check
        if self.messages:
            if "TERMINATE" in str(self.messages[-1].get("content", "")):
                should_terminate = True

        if should_terminate:
            print(f"DEBUG: TERMINATING chat. Explainer detected: {explainer_detected}, has_spoken: {self.explainer_has_spoken}, last_speaker: {last_speaker.name}")
            logger.info(f"🛑 [FORCE TERMINATE] Explainer has spoken or TERMINATE found. Ending GroupChat.")
            return None

        # [EXPLICIT STATE MACHINE]
        print(f"DEBUG: Turn for: {last_speaker.name}. Selection in progress.")
        logger.info(f"🗣️ [StreamingGroupChat] Turn for: {last_speaker.name}")
        
        expert_names = ["学术阅读专家", "日志专家", "配置专家", "通用知识专家"]
        
        # 1. Expert -> Critic
        if any(name in last_speaker.name for name in expert_names):
             return self._get_agent_by_name("质检员")
             
        # 2. Critic -> Explainer (if APPROVE) or back to Expert
        if "质检员" in last_speaker.name:
            last_content = self.messages[-1].get("content", "") if self.messages else ""
            if "APPROVE" in last_content:
                return self._get_agent_by_name("解释专家")
            else:
                if len(self.messages) >= 2:
                    target_name = self.messages[-2].get("name", "")
                    target_agent = self._get_agent_by_name(target_name)
                    if target_agent: return target_agent
                return self._get_agent_by_name("解释专家") # fallback

        # 3. Explainer -> STOP (Secondary check)
        if "解释" in last_speaker.name:
            return None

        # 4. DEFAULT Fallback to AutoGen's internal logic
        # Note: Do NOT set speaker_selection_method=self.select_speaker elsewhere, 
        # as calling super().select_speaker would cause recursion.
        return super().select_speaker(last_speaker, selector)

    def append(self, message: dict, speaker: AssistantAgent):
        message['name'] = speaker.name
        if "解释" in speaker.name:
            self.explainer_has_spoken = True
            logger.info("🚩 Explainer flag set in append.")
            
        super().append(message, speaker)
        
        if self.callback:
            try:
                content = message.get("content", "")
                if not content: return
                clean_content = content.replace("TERMINATE", "").strip()
                if not clean_content: return
                msg_to_send = message.copy()
                msg_to_send['content'] = clean_content 
                msg_to_send['name'] = speaker.name
                self.callback(msg_to_send)
            except Exception as e:
                logger.error(f"Callback failed: {e}")


async def analyze_with_agents(input_text: str, agent_types: list, **kwargs) -> dict:
    callback = kwargs.get("callback")
    """
    启动多智能体协作分析 (Restored Autogen Version)
    :param input_text: 输入文本
    :param agent_types: 如 ["log", "config"]
    :return: 结构化结果
    """
    logger.info(f"🚀 Starting Multi-Agent analysis with Autogen. Input length: {len(input_text)}")
    
    # 检查是否配置了DASHSCOPE_API_KEY
    if not DASHSCOPE_API_KEY:
        logger.warning("未配置 DASHSCOPE_API_KEY，跳过Agent分析")
        return {
            "summary": "Agent分析功能需要配置 DASHSCOPE_API_KEY",
            "reasoning_steps": ["跳过Agent分析：未配置API密钥"],
            "agents_involved": []
        }
    
    try:
        # 1. 准备多智能体环境
        user_proxy, log_expert, config_expert, explainer, paper_expert, general_expert, critic = create_agents()
        
        # 2. 根据 file_type / agent_types 筛选参与的 Agent
        participants = []
        
        if "academic" in agent_types:
            participants = [user_proxy, paper_expert, critic, explainer]
            # 给学术专家的特定指令
            initial_instruction = "请对这篇论文进行深度分析。先由 @学术阅读专家 进行结构化拆解，然后由 @质检员 审查，最后由 @解释专家 总结。"
        elif "log" in agent_types:
            participants = [user_proxy, log_expert, critic, explainer]
            initial_instruction = "请分析这段日志。先由 @日志专家 提取关键错误和根因，然后由 @质检员 审查，最后由 @解释专家 总结。"
        elif "config" in agent_types:
            participants = [user_proxy, config_expert, critic, explainer]
            initial_instruction = "请分析这份配置/代码文档。先由 @配置专家 提取参数和依赖，然后由 @质检员 审查，最后由 @解释专家 总结。"
        elif "book" in agent_types:
            participants = [user_proxy, general_expert, critic, explainer]
            initial_instruction = "请对这本书籍/长文本进行深度分析。先由 @通用知识专家 提取章节摘要和核心概念，然后由 @质检员 审查，最后由 @解释专家 总结。"
        else:
            participants = [user_proxy, general_expert, critic, explainer]
            initial_instruction = "请对这份文档进行深度分析。先由 @通用知识专家 分析核心内容，然后由 @质检员 审查，最后由 @解释专家 总结。"

        # 3. Web Search Augmentation (Native Aliyun Search)
        web_context = ""
        try:
             # Use LLM to extract smart keywords
             keywords = await simple_extract_keywords(input_text)
             if keywords:
                 query = " ".join(keywords[:3]) + " latest trends 2024 2025"
                 logger.info(f"🕸️ [WebSearch-Native] Triggering Aliyun Search for: {query}")
                 
                 from utils.qwen_client import async_call_qwen
                 # Call Qwen with built-in search enabled
                 search_prompt = f"Please search the internet for the latest information (2024-2025) regarding: {query}. Summarize the key findings, new technologies, and future trends."
                 web_context = await async_call_qwen(search_prompt, enable_search=True)
                 
                 if web_context:
                    logger.info("✅ [WebSearch-Native] Search successful.")
                 else:
                    logger.warning("⚠️ [WebSearch-Native] Search returned empty.")
             else:
                 logger.info("🕸️ [WebSearch] No keywords extracted.")
        except Exception as e:
             logger.warning(f"🕸️ [WebSearch] Failed: {e}")

        # 4. 构建任务消息
        task_msg = f"""
        {initial_instruction}

        待分析文本：
        {input_text}

        """
        
        if web_context:
            task_msg += f"\n\n参考的网络背景信息（请基于此信息补充【前沿发展】章节）：\n{web_context}\n"

        task_msg += """
        
        【重要检查点】
        请 @解释专家 在最终总结时，必须包含一个名为 "### 树形思维导图文本描述" 的章节。
        该章节内容必须是 **有意义的领域内容**，严禁使用 "分支1"、"子节点A" 等无意义占位符。
        格式要求为严格的 Markdown 列表，例如：
        ### 树形思维导图文本描述
        【流程要求】
        1. 首先由相关领域的专家（如日志专家、学术专家）发表观点。
        2. 最后由 @解释专家 进行总结。

        【解释专家输出规范】
        @解释专家 请务必按照以下两部分顺序输出，各部分之间用分割线 "---" 隔开：

        **第一部分：深度分析总结**
        请详细阐述背景、问题原因、解决方案或核心观点。这部分是你之前的"思考过程"，请保留并充实。

        ---

        **第二部分：树形思维导图文本描述**
        请包含一个名为 "### 树形思维导图文本描述" 的章节。
        该章节内容必须是 **有意义的领域内容**，严禁使用 "分支1"、"子节点A" 等无意义占位符。
        格式要求为严格的 Markdown 列表。
        
        ---

        **第三部分：核心关键词**
        请输出一个名为 "### 核心关键词" 的章节。
        请仅列出 **3-5个** 最具代表性的核心领域词汇，用英文逗号 separating，例如：
        ### 核心关键词
        TCP拥塞控制, ACK分割攻击, 网络安全, 流量整形

        ---

        **第四部分：前沿发展与未来趋势 (基于联网信息)**
        请输出一个名为 "### 前沿发展与未来趋势" 的章节。
        结合提供的【网络背景信息】，简要分析该技术/主题在当前（2024-2025）的最新进展、新的解决方案或未来的演进方向。
        如果网络信息中没有相关内容，请基于你的知识库进行合理推演。
        
        请确保严格按照此结构输出。
        """

        # 5. Initialize Custom GroupChat
        groupchat = StreamingGroupChat(
            agents=participants, 
            messages=[], 
            max_round=12,
            speaker_selection_method="auto", # Use inheritance to override select_speaker
            callback=callback
        )
        
        # DO NOT set groupchat.speaker_selection_method = groupchat.select_speaker
        # That would cause infinite recursion when select_speaker calls super().

        
        manager = GroupChatManager(
            groupchat=groupchat, 
            llm_config=llm_config
        )

        # 6. 启动对话 (Async)
        logger.info("Chat initiated...")
        chat_result = await user_proxy.a_initiate_chat(
            manager,
            message=task_msg
        )
        
        # 7. 提取结果
        # The last message usually contains the summary from Explainer
        summary = "分析完成"

        explainer_msgs = [
            msg.get("content", "").replace("TERMINATE", "").strip() 
            for msg in groupchat.messages 
            if "解释" in msg.get("name", "")
        ]
        explainer_msgs = [m for m in explainer_msgs if m] # Remove empty
        if explainer_msgs:
            summary = explainer_msgs[-1]
        else:
            summary = groupchat.messages[-1].get("content", "").replace("TERMINATE", "").strip()




        reasoning_steps = [msg.get("content", "") for msg in groupchat.messages]
        agents_involved = [agent.name for agent in participants if agent.name != "用户代理"]
        
        logger.info("✅ Multi-Agent analysis completed successfully.")
        
        result = {
            "summary": summary,
            "reasoning_steps": reasoning_steps,
            "agents_involved": agents_involved,
            "agent_types": agent_types
        }
        return result

    except Exception as e:
        logger.error(f"❌ Multi-agent analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"多智能体分析失败: {str(e)}"}
