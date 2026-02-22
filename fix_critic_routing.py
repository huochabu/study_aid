
import os
import re

target_file = r"e:\study-ai-new\backend\agents\agent_team.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# We want to replace the "Scenario B" block in select_speaker.
# Current content (approximately):
#         # Scenario B: Critic Just Spoke (First Round)
#         if last_speaker.name == "质检员":
#             last_msg = self.messages[-1].get("content", "")
#             if "APPROVE" in last_msg:
#                 logger.info("👉 [StreamingGroupChat] Critic approved. Handoff to Explainer.")
#                 return self._get_agent_by_name("解释专家")
#             else:
#                 logger.info("👉 [StreamingGroupChat] Critic found issues. Forwarding to Explainer to FIX & SUMMARIZE.")
#                 # [FIX] Do not loop back to Expert. Expert is too slow. 
#                 # Let Explainer take the feedback and generate the final trusted version.
#                 return self._get_agent_by_name("解释专家")

# We will use regex to find this block and replace it.
# The key is to match from `if last_speaker.name == "质检员":` up to the return statement.

start_marker = '# Scenario B: Critic Just Spoke (First Round)'
# We'll assume the next block starts with something identifiable or we just capture enough lines.
# Actually, the indentation makes it tricky.

# Let's try to construct the exact string to replace, based on what we saw in view_file previously.
# It seems there might be variations, so I'll write a loop to find the lines and replace.

with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if skip:
        # Check if we are done skipping
        # We assume the block ends when indentation drops or we see specific next comments
        # The previous block ended with `return self._get_agent_by_name("解释专家")` followed by empty line likely.
        # Let's look for the next comment: "# 3. Default behavior"
        if "# 3. Default behavior" in line:
            skip = False
            # Fall through to process this line
        else:
            continue

    if 'if last_speaker.name == "质检员":' in line and "# Scenario B" in lines[i-1]:
        # Found the start (we verify matching the previous line comment too)
        # Actually the loop processes line by line, so let's match the comment line
        pass

    if "# Scenario B: Critic Just Spoke (First Round)" in line:
        # Start new code block
        indent = "        "
        new_lines.append(f"{indent}# Scenario B: Critic Just Spoke (First Round)\n")
        new_lines.append(f"{indent}if last_speaker.name == \"质检员\":\n")
        new_lines.append(f"{indent}    last_msg = self.messages[-1].get(\"content\", \"\")\n")
        new_lines.append(f"{indent}    if \"APPROVE\" in last_msg:\n")
        new_lines.append(f"{indent}        logger.info(\"👉 [StreamingGroupChat] Critic approved. Handoff to Explainer.\")\n")
        new_lines.append(f"{indent}        return self._get_agent_by_name(\"解释专家\")\n")
        new_lines.append(f"{indent}    else:\n")
        new_lines.append(f"{indent}        logger.info(\"👉 [StreamingGroupChat] Critic found issues. Handoff back to PREVIOUS speaker to fix.\")\n")
        new_lines.append(f"{indent}        # [FIXED] Route back to the agent who triggered the critique\n")
        new_lines.append(f"{indent}        if len(self.messages) >= 2:\n")
        new_lines.append(f"{indent}            previous_speaker_name = self.messages[-2].get(\"name\")\n")
        new_lines.append(f"{indent}            logger.info(f\"🔄 Routing back to {{previous_speaker_name}}\")\n")
        new_lines.append(f"{indent}            return self._get_agent_by_name(previous_speaker_name)\n")
        new_lines.append(f"{indent}        else:\n")
        new_lines.append(f"{indent}            return self._get_agent_by_name(\"解释专家\")\n")
        
        # Enable skip mode to ignore the old lines until next block
        skip = True
        continue

    new_lines.append(line)

with open(target_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("✅ Patched Critic Routing Logic.")
