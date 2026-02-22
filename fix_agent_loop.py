
import os

target_file = r"e:\study-ai-new\backend\agents\agent_team.py"

with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Indentation (4 spaces * 2 = 8 spaces inside class/method)
indent = "        "

# New content to replace lines 167-176 (original 1-based, so index 166-176)
# Original block was about 10 lines.
# We want to replace the logic under: # 1. Check if we are in the Final Review phase

# Find start index
start_idx = -1
for i, line in enumerate(lines):
    if "# 1. Check if we are in the Final Review phase" in line:
        start_idx = i
        break

if start_idx != -1:
    print(f"Found block start at line {start_idx + 1}")
    
    # We want to replace from start_idx to the line before "# 2. Check strict handoff"
    # Search for end index
    end_idx = -1
    for i in range(start_idx, len(lines)):
        if "# 2. Check strict handoff" in lines[i]:
            end_idx = i
            break
            
    if end_idx != -1:
        print(f"Found block end at line {end_idx + 1}")
        
        new_block = [
            f"{indent}# 1. Check if we are in the Final Review phase\n",
            f"{indent}if self.explainer_has_spoken:\n",
            f"{indent}    # [UPDATED] Terminate immediately after Explainer speaks to prevent looping\n",
            f"{indent}    if last_speaker.name == '解释专家':\n",
            f"{indent}        logger.info('✅ [StreamingGroupChat] Explainer finished. Terminating immediately as per user request.')\n",
            f"{indent}        return None\n",
            f"{indent}    # Fallback safety\n",
            f"{indent}    if last_speaker.name == '质检员':\n",
            f"{indent}        logger.info('🛑 [StreamingGroupChat] Final Critic Review done. Terminating.')\n",
            f"{indent}        return None\n",
            f"{indent}    return None\n",
            "\n" # Spacer
        ]
        
        # Replace
        new_content = lines[:start_idx] + new_block + lines[end_idx:]
        
        with open(target_file, "w", encoding="utf-8") as f:
            f.writelines(new_content)
            
        print("Successfully patched agent_team.py")
    else:
        print("Could not find end of block")
else:
    print("Could not find start of block")
