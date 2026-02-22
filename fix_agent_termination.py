
import os

target_file = r"e:\study-ai-new\backend\agents\agent_team.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Explainer Prompt to include TERMINATE
old_explainer_sys = 'system_message="你负责整合其他专家的输出，生成清晰、结构化的总结，用于生成思维导图和知识图谱，并且要生成树形的思维导图和知识图谱的文本描述。"'
new_explainer_sys = 'system_message="你负责整合其他专家的输出，生成清晰、结构化的总结。注意：在所有内容输出完毕后，必须另起一行输出：TERMINATE"'

if old_explainer_sys in content:
    content = content.replace(old_explainer_sys, new_explainer_sys)
    print("✅ Updated Explainer Prompt with TERMINATE instruction.")
else:
    print("⚠️ Could not match Explainer Prompt exactly. Trying looser match.")
    # Attempt looser match if needed or proceed check

# 2. Update UserProxyAgent to handle TERMINATE
# Look for: max_consecutive_auto_reply=5,
# Replace with: max_consecutive_auto_reply=5, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),

search_str = 'max_consecutive_auto_reply=5,'
replace_str = 'max_consecutive_auto_reply=5, is_termination_msg=lambda x: "TERMINATE" in str(x.get("content", "")),'

if search_str in content:
    # Be careful not to replace it multiple times if run repeatedly
    if "is_termination_msg" not in content:
        content = content.replace(search_str, replace_str)
        print("✅ Updated UserProxyAgent to recognize TERMINATE.")
    else:
        print("ℹ️ UserProxyAgent already has restriction logic.")

# 3. Add safety to Agent Team to ensure Explainer Prompt update worked if exact match failed
# (We can use regex to force it if step 1 failed)
import re
if "TERMINATE" not in content:
    # Use regex to find Explainer definition
    pattern = r'(name="解释专家",\s+system_message=")(.*?)(")'
    def repl(m):
        return m.group(1) + m.group(2) + " 在最后必须输出 TERMINATE" + m.group(3)
    
    content = re.sub(pattern, repl, content, flags=re.DOTALL)
    print("✅ Forced Explainer Prompt update via Regex.")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
