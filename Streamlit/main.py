import streamlit as st
import streamlit.components.v1 as components
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage
import requests
import json
import os
import base64

st.set_page_config(layout="wide")
DEBUG_MODE = False
TEST_DEBUG_MODE = False

# Load Upstage API key
upstage_api_key = st.secrets.get("UPSTAGE_API_KEY") or os.getenv("UPSTAGE_API_KEY")

st.title("📄FORMula")

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

        text_content = result.get("content", {}).get("html", "").strip() # only use content.text

        if not text_content:
            st.warning("No plain text found in the document (content.text is empty).")

        if TEST_DEBUG_MODE:
            # Debug: Show raw content
            st.subheader("📦 Raw 'content.text' from Document API")
            st.code(text_content[:3000], language="markdown")

        return text_content, None

    except Exception as e:
        return None, e
    
def stream_response(prompt):
    chat = ChatUpstage(
        upstage_api_key=upstage_api_key,
        model_name="solar-pro-241126",
        temperature=0.7,
        stream=True,
    )

    # Use `stream_raw` instead of __call__ to get the streaming generator
    stream = chat.stream([HumanMessage(content=prompt)])

    for chunk in stream:
        # Each chunk should be a ChatMessage — yield its content
        if hasattr(chunk, "content"):
            yield chunk.content

# Initialize step
with tab1:
    st.header("Step 1: Input prompt with initial form")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    top_container = st.container()

    with st.form("chat_input_form", clear_on_submit=False):
        user_text = st.text_area("Type your message")
        uploaded_file = st.file_uploader("Upload a PDF (optional)", type=["pdf"])
        force_ocr = st.checkbox("Force OCR (for scanned/image PDFs)", value=False)
        submit_button = st.form_submit_button("Send")
        
    with top_container:
        status_placeholder = st.empty() 

    if submit_button and (user_text or uploaded_file):
        with top_container:
            status_placeholder.info("Loading...")

            user_msg = {
                "text": user_text,
                "file": uploaded_file
            }
            st.session_state.chat_history.append(user_msg)

            if TEST_DEBUG_MODE:
                # Show user message
                with st.chat_message("user"):
                    if user_msg["text"]:
                        st.markdown(user_msg["text"])
                    if user_msg["file"]:
                        st.markdown("Uploaded PDF:")
                        st.write(user_msg["file"].name)

            # Initialize prompt
            prompt = user_msg["text"]
            extracted_text = ""
            
            col1, col2 = st.columns(2, gap="large")

            # If PDF exists, extract and append context
            if uploaded_file:
                file_bytes = uploaded_file.read()
                extracted_text, error = process_document_with_upstage(file_bytes)

                if extracted_text:
                    if TEST_DEBUG_MODE:
                        st.subheader("📄 Parsed Document Content")
                        st.code(extracted_text[:3000], language="markdown")

                    prompt += f"\n\nAdditional context from document:\n{extracted_text}"

                    if TEST_DEBUG_MODE:
                        st.subheader("🖥️ Rendered Document HTML")
                        st.components.v1.html(extracted_text, height=600, scrolling=True)
                elif error:
                    status_placeholder.error(f"Document API error: {error}")

                # Show PDF viewer
                base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
                pdf_display = f"""
                <embed 
                    src="data:application/pdf;base64,{base64_pdf}" 
                    width="700" 
                    height="1000" 
                    type="application/pdf">
                """
                with col1:
                    st.subheader("PDF Editor")
                    st.markdown(pdf_display, unsafe_allow_html=True)

            else:
                status_placeholder.warning("No PDF uploaded, defaulting to prompt response.")

            # Display assistant response
            with col2:
                status_placeholder.success("✅ Done!")
                
                st.subheader("🤖 Solar Response")
                with st.chat_message("assistant"):
                    st.write_stream(stream_response(prompt))

## STAGE 2
with tab2:
    st.header("Step 2: Upload form for internal scan")

    top_container_2 = st.container()
    
    with st.form("pdf_edit_form", clear_on_submit=False):
        pdf_file_edit = st.file_uploader("Upload editted PDF file", type=["pdf"])
        # force_ocr_edit = st.checkbox("Force OCR (for scanned/image PDFs)", value=False)
        submit_pdf_button = st.form_submit_button("Send PDF")

    if submit_pdf_button:
        with top_container_2:
            status_placeholder2 = st.empty()

            if pdf_file_edit is not None: 
                # Streamlit's uploaded_file is already a file-like object
                files = {
                    "file": (pdf_file_edit.name, pdf_file_edit, "application/pdf")
                }

                response = requests.post("http://localhost:8001/check-pdf", files=files)

                if response.status_code == 200:
                    status_placeholder2.success("Check complete.")
                else:
                    status_placeholder2.error(f"Error: {response.status_code}")
                pdf_file_edit.seek(0)
                
                # PDF Viewer: Display raw PDF as embedded iframe
                file_bytes_edit = pdf_file_edit.read()
                base64_pdf_edit = base64.b64encode(file_bytes_edit).decode('utf-8')
                pdf_display_edit = f"""
                    <embed 
                        src="data:application/pdf;base64,{base64_pdf_edit}" 
                        width="700" 
                        height="1000" 
                        type="application/pdf">
                """
                
                col1, col2 = st.columns(2, gap="medium", vertical_alignment="top", border=False)
                
                # Add content to the first column
                with col1:
                    st.subheader("PDF Editor")
                    st.markdown(pdf_display_edit, unsafe_allow_html=True)

                # Add content to the second column
                with col2:
                    st.subheader("Internal scan Response")

                    # Send prompt to Solar (ChatUpstage)
                    if response.status_code == 200:
                        st.json(response.json())
                    else:
                        status_placeholder2.error(response.text)
            else:
                status_placeholder2.error(f"Please upload a file")

