import fitz  # pip install pymupdf

def get_pdf_page_as_image(pdf_file: str, page_number: int) -> bytes:
    """
    Convert a PDF page to an image and return the image bytes.
    
    Args:
        pdf_file (str): Path to the PDF file
        page_number (int): Page number to convert (1-based index)
    
    Returns:
        bytes: Image bytes in PNG format
    
    Raises:
        Exception: If there's an error opening the PDF or converting the page
    """
    try:
        # Open the PDF file
        doc = fitz.open(pdf_file)
        
        # Load the specified page (convert to 0-based index)
        page = doc.load_page(page_number - 1)
        pix = page.get_pixmap()
        
        # Convert to PNG bytes and return
        return pix.tobytes("png")
        
    except Exception as e:
        raise Exception(f"PDF 페이지 변환 중 오류 발생: {e}")

# Example usage:
if __name__ == "__main__":
    pdf_path = "../Database/Local/test/original.pdf"
    page_num = 1
    image_bytes = get_pdf_page_as_image(pdf_path, page_num)
    
    # You can save the image bytes to a file if needed
    with open("output.png", "wb") as f:
        f.write(image_bytes)