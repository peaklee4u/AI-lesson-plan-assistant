import pdfplumber
from typing import Optional

def extract_text_from_pdf(pdf_file) -> Optional[str]:
    """
    Extracts text from an uploaded PDF file using pdfplumber.
    
    Args:
        pdf_file: The uploaded PDF file object (from Streamlit).
        
    Returns:
        The extracted text as a string, or None if extraction fails.
    """
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Extracting words with their positions to handle layouts better if needed
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None
