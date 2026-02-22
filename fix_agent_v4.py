
import os

target_file = r"e:\study-ai-new\backend\agents\agent_team.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Critic Prompt (Relaxed)
old_critic_msg = """你是一名严格的内容质检员 (Critic)。
        
        【严格禁止】
        ❌ 严禁生成文章摘要或总结。
        ❌ 严禁重复专家的分析内容。
        ❌ 严禁输出大段文本。

        【唯一任务】
        仅检查以下三点（**必须先确认专家真的没写，再提出批评**）：
        1. 逻辑漏洞：结论是否有证据支持？
        2. 遗漏视角：是否忽略了安全性、性能或边缘情况？（注意：如果专家已提及相关概念，请勿视为遗漏）
        3. 格式规范：是否清晰？
        
        【输出规则】
        - 如果分析质量合格，或专家已经覆盖了核心点，请 **仅回复** 一次单词："APPROVE"。
        - 如果发现 **真正** 的问题，请用 **列表形式** 列出 2-3 点非常简短的修改建议（每条不超过20字）。
        """

new_critic_msg = """你是一名友好的内容检查员。
        
        你的任务是确保专家输出了核心内容（如创新点、方法等），而**不必**过于纠结细节或深度。
        除非内容完全离题或空白，否则请尽量**放行**。

        【检查标准】
        - 是否有基本的内容输出？
        - 格式是否大致清晰？
        
        【输出规则】
        - 只要不是严重错误，请直接回复："APPROVE"。
        - 如果确实缺失核心内容，请用一句话指出。
        """

# We look for the start of the string to replace, as whitespace might vary.
search_str = 'name="质检员",'
if search_str in content:
    # We find the system_message arg
    # This is a bit risky with regex, let's try strict replacement if possible.
    # The previous view showed the content clearly.
    # We will try to replace the string snippet.
    
    # Let's locate the 'system_message="""' after 'name="质检员",'
    start_idx = content.find('name="质检员"')
    if start_idx != -1:
        # scan forward for system_message
        sys_msg_start = content.find('system_message="""', start_idx)
        if sys_msg_start != -1:
            sys_msg_end = content.find('""",', sys_msg_start)
            if sys_msg_end != -1:
                # Replace the content inside """ ... """
                original_text = content[sys_msg_start+18 : sys_msg_end] # +18 for system_message=""" 
                
                # We replace with new message
                content = content[:sys_msg_start+18] + new_critic_msg + content[sys_msg_end:]
                print("✅ Updated Critic Prompt to Relaxed Version.")

# 2. Fix Explainer Loop Logic Check
# We want to catch the case where Explainer spoke and we are waiting.
# Users said "Wait long time then speak again". 
# This implies LLM generation happens.
# We will inject a failsafe in select_speaker that checks ANY message history.

failsafe_logic = """
        # [FAILSAFE] Check message history directly
        # Sometimes flags fail. If we see '解释专家' in the last message name, TERMINATE.
        if self.messages:
            last_msg_name = self.messages[-1].get('name', '')
            if '解释' in last_msg_name:
                logger.info(f"🛑 [Failsafe] Detected '解释专家' in message history. Terminating now.")
                self.explainer_has_spoken = True # Sync flag
                return None
"""

# Insert this at the TOP of select_speaker
fn_def = 'def select_speaker(self, last_speaker, selector):'
if fn_def in content:
    replacement = fn_def + "\n" + failsafe_logic
    content = content.replace(fn_def, replacement)
    print("✅ Injected Failsafe Termination Logic.")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
