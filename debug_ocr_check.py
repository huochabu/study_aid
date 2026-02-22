import sys
import os
import types

# MOCK LOGIC FROM ocr_service.py
sys.modules['langchain'] = types.ModuleType('langchain')
sys.modules['langchain.docstore'] = types.ModuleType('langchain.docstore')
sys.modules['langchain.docstore.document'] = types.ModuleType('langchain.docstore.document')
sys.modules['langchain.text_splitter'] = types.ModuleType('langchain.text_splitter')

class MockDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}
sys.modules['langchain.docstore.document'].Document = MockDocument

class MockRecursiveCharacterTextSplitter:
    def __init__(self, **kwargs): pass
    def split_documents(self, documents): return documents
sys.modules['langchain.text_splitter'].RecursiveCharacterTextSplitter = MockRecursiveCharacterTextSplitter

import pkgutil
if not hasattr(pkgutil, 'ImpImporter'):
    class MockImpImporter:
        def __init__(self, path): self.path = path
    pkgutil.ImpImporter = MockImpImporter

try:
    print("Attempting to import paddleocr (with mocks)...")
    from paddleocr import PaddleOCR
    print("PaddleOCR imported successfully.")
    
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    print("PaddleOCR initialized successfully.")
    
except ImportError as e:
    print(f"ImportError: {e}")
    print("It seems paddleocr is not installed. Please run: pip install paddlepaddle paddleocr")
except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
