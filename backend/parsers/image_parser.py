# image_parser.py

import os

# 强制使用本地模型，禁止任何网络下载
os.environ["PADDLEOCR_HOME"] = "E:/documap/.paddleocr_cache"  # 避免默认缓存干扰

from paddleocr import PaddleOCR

# 使用绝对路径，确保在任何工作目录下都能找到模型
DET_MODEL_DIR = r"E:\documap\models\paddleocr\ch_PP-OCRv4_det_infer"
REC_MODEL_DIR = r"E:\documap\models\paddleocr\ch_PP-OCRv4_rec_infer"
CLS_MODEL_DIR = r"E:\documap\models\paddleocr\ch_ppocr_mobile_v2.0_cls_infer"

# 初始化 OCR 引擎（完全离线）
ocr_engine = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    use_gpu=False,
    det_model_dir=DET_MODEL_DIR,
    rec_model_dir=REC_MODEL_DIR,
    cls_model_dir=CLS_MODEL_DIR,
    download_model=False,  # 关键：禁止自动下载
    show_log=False         # 可选：关闭日志输出
)

def extract_text_from_image(image_path: str) -> str:
    result = ocr_engine.ocr(image_path, cls=True)
    text = ""
    for line in result:
        if line is None:
            continue
        for word_info in line:
            text += word_info[1][0] + "\n"
    return text.strip()