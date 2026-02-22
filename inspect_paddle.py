import sys
import types
import os

# MOCK LOGIC TO BYPASS IMPORT ERROR
sys.modules['langchain'] = types.ModuleType('langchain')
sys.modules['langchain.docstore'] = types.ModuleType('langchain.docstore')
sys.modules['langchain.docstore.document'] = types.ModuleType('langchain.docstore.document')
sys.modules['langchain.text_splitter'] = types.ModuleType('langchain.text_splitter')

# DEFINE MOCK CLASSES
class MockDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}
sys.modules['langchain.docstore.document'].Document = MockDocument

class MockRecursiveCharacterTextSplitter:
    def __init__(self, **kwargs): pass
    def split_documents(self, documents): return documents
sys.modules['langchain.text_splitter'].RecursiveCharacterTextSplitter = MockRecursiveCharacterTextSplitter

from paddleocr import PaddleOCR
import inspect

print("Inspecting PaddleOCR class...")
try:
    # Print the docstring
    print("Docstring:")
    print(PaddleOCR.__doc__)
    
    # Print init signature
    print("\n__init__ signature:")
    print(inspect.signature(PaddleOCR.__init__))
except Exception as e:
    print(f"Error inspecting: {e}")
