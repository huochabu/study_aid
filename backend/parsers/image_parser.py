# image_parser.py

# 使用统一的OCR服务
from backend.services.ocr_service import ocr_service

def extract_text_from_image(image_path: str) -> str:
    """提取图片文本（OCR）"""
    return ocr_service.extract_text(image_path)