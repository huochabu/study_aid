# agents/agent_team.py
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import os

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请在 .env 文件中设置 DASHSCOPE_API_KEY")

llm_config = {
    "config_list": [{
        "model": "qwen-max",
        "api_key": DASHSCOPE_API_KEY,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    }],
    "temperature": 0.7,
}

def create_agents():
    """工厂函数：每次创建新 Agent 实例，避免状态污染"""
    log_expert = AssistantAgent(
        name="日志专家",
        system_message="你是一名日志分析专家。请从日志中提取错误、IP、时间，并推断根因。",
        llm_config=llm_config,
        code_execution_config=False
    )

    config_expert = AssistantAgent(
        name="配置专家",
        system_message="你擅长从技术文档中抽取参数、依赖关系，构建结构化配置知识。",
        llm_config=llm_config,
        code_execution_config=False
    )

    explainer = AssistantAgent(
        name="解释专家",
        system_message="你负责整合其他专家的输出，生成清晰、结构化的总结，用于生成思维导图和知识图谱，并且要生成树形的思维导图和知识图谱的文本描述。",
        llm_config=llm_config,
        code_execution_config=False
    )

    user_proxy = UserProxyAgent(
        name="用户代理",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        code_execution_config={"use_docker": False}
    )
    return user_proxy, log_expert, config_expert, explainer

def analyze_with_agents(input_text: str, agent_types: list) -> dict:
    """
    按需启动多智能体协作
    :param input_text: 输入文本
    :param agent_types: 如 ["log", "config"]
    :return: 结构化结果
    """
    user_proxy, log_expert, config_expert, explainer = create_agents()
    
    # 动态选择参与的 Agent
    selected_agents = [user_proxy]
    if "log" in agent_types:
        selected_agents.append(log_expert)
    if "config" in agent_types:
        selected_agents.append(config_expert)
    selected_agents.append(explainer)  # Explainer 总是参与

    groupchat = GroupChat(
        agents=selected_agents,
        messages=[],
        max_round=8,
        speaker_selection_method="round_robin"
    )

    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        code_execution_config={"use_docker": False}
    )

    try:
        user_proxy.initiate_chat(
            manager,
            message=f"请协作分析以下技术内容：\n\n{input_text}"
        )

        if groupchat.messages:
            last_msg = groupchat.messages[-1]["content"]
            reasoning = [msg["content"] for msg in groupchat.messages if msg.get("content")]
            return {
                "summary": last_msg,
                "reasoning_steps": reasoning,
                "agents_involved": [a.name for a in selected_agents]
            }
        else:
            return {"error": "无有效消息返回"}
    except Exception as e:
        return {"error": f"多智能体分析失败: {str(e)}"}