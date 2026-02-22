import os
from pypdf import PdfReader

def read_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        # Read first 10 pages and some random pages to get an idea, or full text if not too large
        # For specs, headers usually in first few pages.
        for i, page in enumerate(reader.pages):
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading {file_path}: {e}"

files = [
    "e:\\study-aid\\第5组-需求规格.pdf", 
    "e:\\study-aid\\第五组-设计规格说明（1.9）.pdf"
]

for f in files:
    print(f"--- Content of {os.path.basename(f)} ---")
    content = read_pdf(f)
    print(content[:5000]) # Print first 5000 extracted chars to avoid overwhelming output
    print(f"\n--- End of {os.path.basename(f)} ---\n")
