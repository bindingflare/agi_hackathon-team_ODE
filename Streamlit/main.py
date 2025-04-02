import streamlit as st
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage
import requests
import json
import os
import base64

# Load Upstage API key
upstage_api_key = st.secrets.get("UPSTAGE_API_KEY") or os.getenv("UPSTAGE_API_KEY")

st.title("Chatbot with Solar & Document Parsing")

tab1, tab2 = st.tabs(["Step 1: Form Upload", "Step 2: Form fix"])

# Document processing function
def process_document_with_upstage(file_bytes):
    url = "https://api.upstage.ai/v1/document-digitization"
    headers = {
        "Authorization": f"Bearer {upstage_api_key}"
    }
    files = {
        "document": ("document.pdf", file_bytes, "application/pdf")
    }
    data = {
        "ocr": "force" if force_ocr else "auto",
        "coordinates": "true",
        "chart_recognition": "true",
        "output_formats": json.dumps(["html"]),
        "model": "document-parse",
        "base64_encoding": json.dumps([])
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        result = response.json()

        # ✅ Only use content.text
        text_content = result.get("content", {}).get("html", "").strip()

        if not text_content:
            st.warning("No plain text found in the document (content.text is empty).")

        # Debug: Show raw content
        st.subheader("📦 Raw 'content.text' from Document API")
        st.code(text_content[:3000], language="markdown")

        return text_content

    except Exception as e:
        st.error(f"Document API error: {e}")
        return None
    

# Initialize step
with tab1:
    st.header("Step 1: Input Message and Upload PDF")
    user_input = st.text_input("Enter your prompt:")
    pdf_file = st.file_uploader("Or upload a PDF file (optional)", type=["pdf"])
    force_ocr = st.checkbox("Force OCR (for scanned/image PDFs)", value=False)

    # Handle submission
    if st.button("Send"):
        prompt = user_input
        extracted_text = ""

        # Process PDF if uploaded
        if pdf_file is not None:
            file_bytes = pdf_file.read()
            extracted_text = process_document_with_upstage(file_bytes)

            if extracted_text:
                st.subheader("📄 Parsed Document Content")
                st.code(extracted_text[:3000], language="markdown")  # Show first 3,000 chars

                # Append to prompt
                prompt += f"\n\nAdditional context from document:\n{extracted_text}"

                # Display the HTML (extracted text)
                st.subheader("🖥️ Rendered Document HTML")
                st.components.v1.html(extracted_text, height=600, scrolling=True)

            # PDF Viewer: Display raw PDF as embedded iframe
            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
            pdf_display = f"""
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}" 
                    width="700" 
                    height="1000" 
                    type="application/pdf">
                </iframe>
            """

            # pdf_display_http = f'<embed src=“http://localhost:8900/{file.name}” type=“application/pdf” width=“1000px” height=“1100px”></embed>'

            col1, col2 = st.columns(2, gap="medium", vertical_alignment="top", border=False)

            # Add content to the first column
            with col1:
                st.header("PDF Editor")
                st.markdown(pdf_display, unsafe_allow_html=True)

            # Add content to the second column
            with col2:
                st.header("🤖 Solar Response")

                # Send prompt to Solar (ChatUpstage)e
                chat = ChatUpstage(
                    upstage_api_key=upstage_api_key,
                    model_name="solar-pro-241126",
                    temperature=0.7,
                )
                response = chat([HumanMessage(content=prompt)])
                
                st.write(response.content)
                st.session_state.step = 2  # Move to next step
                # st.experimental_rerun()  # Refresh the app with new state

## STAGE 2
with tab2:
    pdf_file_edit = st.file_uploader("Upload editted PDF file", type=["pdf"])

    if st.button("Send PDF") and pdf_file_edit is not None:
        # Streamlit's uploaded_file is already a file-like object
        files = {
            "file": (pdf_file_edit.name, pdf_file_edit, "application/pdf")
        }

        response = requests.post("http://localhost:8001/check-pdf", files=files)

        if response.status_code == 200:
            st.success("Check complete.")
        else:
            st.error(f"Error: {response.status_code}")
        pdf_file_edit.seek(0)
        
        # PDF Viewer: Display raw PDF as embedded iframe
        file_bytes_edit = pdf_file_edit.read()
        base64_pdf_edit = base64.b64encode(file_bytes_edit).decode('utf-8')
        pdf_display_edit = f"""
            <iframe 
                src="data:application/pdf;base64,{base64_pdf_edit}" 
                width="700" 
                height="1000" 
                type="application/pdf">
            </iframe>
        """
        
        col1, col2 = st.columns(2, gap="medium", vertical_alignment="top", border=False)
        
        # Add content to the first column
        with col1:
            st.header("PDF Editor")
            st.markdown(pdf_display_edit, unsafe_allow_html=True)

        # Add content to the second column
        with col2:
            st.header("Internal scan Response")

            # Send prompt to Solar (ChatUpstage)
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.write(response.text)
    else:
        st.error(f"Please uploaded a file")

