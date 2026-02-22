
import os

target_file = r"e:\study-ai-new\backend\agents\agent_team.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update create_agents to include is_termination_msg for ALL agents
# and ensure they all look for TERMINATE
content = content.replace(
    'llm_config=llm_config,',
    'llm_config=llm_config, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),'
)
# Re-fix the user_proxy which already has it to avoid double-assignment if needed, 
# but search/replace should be fine if we are careful. Actually, let's be more precise.

# 2. Refactor StreamingGroupChat for extreme robustness
clean_class = """
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
        \"\"\"Extremely aggressive speaker selection and termination.\"\"\"
        
        # [CRITICAL] check if explainer has spoken or termination signal is present
        should_terminate = self.explainer_has_spoken
        
        if self.messages:
            last_msg = self.messages[-1]
            last_msg_name = str(last_msg.get('name', ''))
            last_msg_content = str(last_msg.get('content', ''))
            
            if '解释' in last_msg_name or "TERMINATE" in last_msg_content:
                should_terminate = True

        if should_terminate:
            logger.info(f"🛑 [FORCE TERMINATE] Explainer has spoken or TERMINATE found. Ending GroupChat.")
            return None

        # [EXPLICIT STATE MACHINE]
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

        # 3. Explainer -> STOP (Handled by first block)
        if "解释" in last_speaker.name:
            return None

        # 4. DEFAULT Fallback
        logger.info(f"⚠️ Hitting fallback for {last_speaker.name}. Using super().select_speaker")
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
"""

import re
pattern = r"class StreamingGroupChat\(GroupChat\):.*?async def analyze_with_agents"
content = re.sub(pattern, clean_class + "\n\nasync def analyze_with_agents", content, flags=re.DOTALL)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ Refactored agent_team.py with aggressive termination.")
