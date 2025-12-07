# backend/uploads/file_manager.py
import os
import json
from pathlib import Path

def get_parsed_text_from_file(file_id: str) -> List[str]:
    # 假设解析后的文本保存在 uploads/parsed/{file_id}.json
    parsed_path = Path("uploads") / "parsed" / f"{file_id}.json"
    if not parsed_path.exists():
        return []

    with open(parsed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("text_chunks", [])