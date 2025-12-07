# download_model.py
from huggingface_hub import snapshot_download
import os

model_dir = "E:/documap/models/bge-small-zh"
os.makedirs(model_dir, exist_ok=True)

snapshot_download(
    repo_id="BAAI/bge-small-zh",
    local_dir=model_dir,
    local_dir_use_symlinks=False
)
print(f"✅ 模型已完整下载到: {model_dir}")