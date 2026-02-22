
import pdfplumber

def extract_headings(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total Pages: {len(pdf.pages)}")
            text = ""
            for i in range(min(5, len(pdf.pages))): # Read first 5 pages for TOC
                page = pdf.pages[i]
                text += page.extract_text() + "\n"
            print(text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("--- Requirements Spec ---")
    extract_headings("e:\\study-aid\\第5组-需求规格.pdf")
    print("\n--- Design Spec ---")
    extract_headings("e:\\study-aid\\第五组-设计规格说明（1.9）.pdf")
