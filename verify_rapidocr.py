import logging
import traceback

print("Checking RapidOCR installation...")
try:
    from rapidocr_onnxruntime import RapidOCR
    print("Import successful.")
    
    ocr = RapidOCR()
    print("Initialization successful.")
    
    # Optional: Test inference
    # result, elapse = ocr('some_image.jpg')
    print("RapidOCR is ready to use.")
except ImportError:
    print("Error: rapidocr_onnxruntime not found. Please run: pip install rapidocr-onnxruntime")
except Exception as e:
    print(f"Error initializing RapidOCR: {e}")
    traceback.print_exc()
