import re
import uuid
import logging

logger = logging.getLogger(__name__)

def parse_markdown_mindmap(text: str) -> dict:
    """
    Parse a markdown list (tree structure) into a mindmap JSON format compatible with the frontend.
    Looking for a section starting with "### 思维导图" or "Mind Map" and parsing the bullet points.
    """
    if not text:
        return None

    # 1. Extract the mindmap section
    # Regex to find a header like "### 思维导图..." until the next "###" or end of string
    section_pattern = r"(?:###\s*(?:思维导图|Mind Map|Tree Structure).*?)(?:\n###|\Z)"
    match = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)
    
    content_to_parse = ""
    if match:
        content_to_parse = match.group(0)
    else:
        # Fallback: try to find the largest block of bullet points?
        # Or just parse the whole text if it looks like a list?
        # For now, let's look for known headers from our Agent prompts.
        # "### 树形思维导图文本描述" is explicitly mentioned in the user log.
        if "### 树形思维导图文本描述" in text:
             parts = text.split("### 树形思维导图文本描述")
             if len(parts) > 1:
                 # Take the part after the header, stop at next ###
                 sub_content = parts[1]
                 if "###" in sub_content:
                     content_to_parse = sub_content.split("###")[0]
                 else:
                     content_to_parse = sub_content
        else:
             # If no header found, return None to let the KG fallback take over
             return None

    if not content_to_parse.strip():
        return None

    # 2. Parse the bullet points
    lines = content_to_parse.split('\n')
    root = {"id": "root", "topic": "核心分析", "children": []}
    
    # Python doesn't have pointers, so we keep a stack of (level, node)
    # Level: indent size or depth
    stack = [(-1, root)] 
    
    # Regex for bullet points: optional whitespace, then -, *, or + followed by space
    # And capture the rest of the line
    bullet_pattern = r"^(\s*)(?:[-*+]|(?:\d+\.))\s+(.*)"
    
    # Try to find a root topic from the first non-empty line that isn't a bullet?
    # Or just use the first bullet as a child of virtual root
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
            
        # Check if it's a code block marker, skip
        if line.strip().startswith("```"):
            continue
            
        match = re.match(bullet_pattern, line)
        if match:
            indent_str = match.group(1)
            content = match.group(2).strip()
            
            # Calculate indent level (expanded tabs to spaces if needed, but usually simple)
            indent_level = len(indent_str)
            
            # Create new node
            # topic might contain bolding **text**, remove it for cleaner mindmap?
            # Or keep it. Frontend might render markdown. Let's keep it but remove wrapper chars if easy.
            # Actually, `markmap` or similar libs handle markdown. 
            # But our frontend uses a custom renderer? Let's just clean simple **
            clean_topic = content.replace("**", "")
            
            new_node = {
                "id": str(uuid.uuid4()),
                "topic": clean_topic,
                "children": []
            }
            
            # Find parent in stack
            # Pop elements that are deeper or same level (strictly deeper? No, same level means we are sibling)
            # Parent must have strictly smaller indent level
            
            while stack and stack[-1][0] >= indent_level:
                stack.pop()
                
            if not stack:
                # Should not happen if we kept root at -1, but just in case
                stack.append((-1, root))
                
            parent_node = stack[-1][1]
            parent_node["children"].append(new_node)
            
            stack.append((indent_level, new_node))
            
    # If we parsed nothing, return None
    if not root["children"]:
        return None
        
    return {"root": root}
