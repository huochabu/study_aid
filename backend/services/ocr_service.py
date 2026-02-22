import os
import logging
import traceback

# Setup logging
logger = logging.getLogger(__name__)

class OCRService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRService, cls).__new__(cls)
            cls._instance._init_ocr()
        return cls._instance
    
    def _init_ocr(self):
        """Initialize RapidOCR (ONNX Runtime)"""
        try:
            logger.info("Initializing RapidOCR engine...")
            from rapidocr_onnxruntime import RapidOCR
            
            # Initialize with default models (ch)
            # RapidOCR automatically handles model downloading and ONNX runtime session
            self.ocr = RapidOCR() 
            
            logger.info("RapidOCR initialized successfully.")
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {str(e)}")
            logger.error(traceback.format_exc())
            self.initialized = False
            self.error_message = str(e)
    
    def extract_text(self, image_path: str) -> dict:
        """Extract text from image"""
        if not self.initialized:
            # Fallback if OCR failed to init
            return {"text": "", "layout": []}
            
        try:
            logger.info(f"Processing image with RapidOCR: {image_path}")
            
            # RapidOCR call: result, elapse = engine(img_path)
            # result structure: [[box, text, score], ...] 
            # box is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            result, elapse = self.ocr(image_path)
            
            full_text = ""
            layout_data = []
            
            if result:
                for item in result:
                    # item structure: [box, text, score]
                    # box: list of 4 points [[x,y],...]
                    box, text, score = item
                    if text:
                        full_text += text + "\n"
                        layout_data.append({
                            "text": text,
                            "box": box
                        })
            
            full_text = full_text.strip()
            logger.info(f"RapidOCR extraction complete. Length: {len(full_text)}")
            
            return {
                "text": full_text,
                "layout": layout_data
            }
            
        except Exception as e:
            logger.error(f"RapidOCR extraction failed: {str(e)}")
            logger.error(traceback.format_exc())
            return {"text": "", "layout": []}

# Create global instance
ocr_service = OCRService()