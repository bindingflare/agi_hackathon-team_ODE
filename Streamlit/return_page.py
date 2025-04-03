import streamlit as st
import fitz  

st.title("PDF Viewer (PyMuPDF)")

#TODO
# rag 이후 반환된 정보에서
# source file and page should be retrived

source_file = "GUIDE_NONGMOguide.json"
page = 2

pdf_file = "../Database/Local/test/" + source_file[:-5] + ".pdf"

try:
    doc = fitz.open(pdf_file)
    # Pages are 0-indexed, so subtract 1
    page = doc.load_page(page - 1)

    pix = page.get_pixmap()
    img_bytes = pix.tobytes("png")

    st.image(img_bytes, caption=f"PDF의 페이지 {page}", use_column_width=True)

except Exception as e:
    st.error(f"PDF 페이지 변환 중 오류 발생: {e}")