from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 使用中文 BERT 作为嵌入模型（轻量）
tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")
model = AutoModel.from_pretrained("bert-base-chinese")

def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

def detect_anomalies_llm(log_lines, window_size=50):
    anomalies = []
    # 构建正常行为描述（前 N 行）
    normal_window = log_lines[:window_size]
    if not normal_window:
        return anomalies
    
    normal_desc = " ".join(normal_window)
    normal_emb = get_embedding(normal_desc)
    
    for i, line in enumerate(log_lines[window_size:], start=window_size):
        line_emb = get_embedding(line)
        sim = cosine_similarity([normal_emb], [line_emb])[0][0]
        if sim < 0.6:  # 阈值可调
            anomalies.append({
                "line_number": i + 1,
                "text": line,
                "reason": f"语义偏离度高 (相似度={sim:.2f})"
            })
    return anomalies