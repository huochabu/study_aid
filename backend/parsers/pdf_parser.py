import pdfplumber

def extract_text_from_pdf(pdf_path: str) -> str:
    """从 PDF 文件中提取纯文本"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                if page is not None:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
    except Exception as e:
        print(f"PDF 解析出错: {e}")
        return ""
    return text.strip()