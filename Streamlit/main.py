import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import base64
import sys
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage
import requests
from sidebar import init_chat_state, render_chat_button, render_chat_interface
from utils import (
    save_conversation, 
    load_conversations, 
    perform_web_search, 
    save_search_result, 
    load_search_history,
    load_user_info,
    enhance_prompt_with_web_search
)
import itertools
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 페이지 설정
st.set_page_config(layout="wide")

# 채팅 상태 및 인터페이스 초기화 (sidebar.py의 기능 활용)
init_chat_state()
render_chat_button()
render_chat_interface()

DEBUG_MODE = False
TEST_DEBUG_MODE = False

# Upstage API key 로드
upstage_api_key = st.secrets.get("UPSTAGE_API_KEY") or os.getenv("UPSTAGE_API_KEY")

st.title("📄FORMula")

tab1, tab2 = st.tabs(["Step 1: Form Upload", "Step 2: Form Validate"])

# --- Step 1: Form Upload ---
with tab1:
    st.header("Step 1: Input prompt with initial form")
    
    top_container = st.container()

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if "fetch_history_toggle" not in st.session_state:
            st.session_state.fetch_history_toggle = False
        if st.toggle("Fetch my history", key="fetch_history_toggle"):
            if not st.session_state.get("history_loaded", False):
                user_info = load_user_info()
                if user_info:
                    # 예시: 이전 정보 기반 초기 프롬프트 생성
                    history_prompt = f"Based on previous info:\nCompany: {user_info.get('company_name', '')}\nIndustry: {user_info.get('industry', '')}\n"
                    st.session_state.history_prompt = history_prompt
                    st.session_state.history_loaded = True
                    st.success("History loaded successfully!")
                else:
                    st.warning("No previous history found.")
        else:
            st.session_state.history_loaded = False
    with col2:
        if "formula_web_search_enabled" not in st.session_state:
            st.session_state.formula_web_search_enabled = False
        if st.toggle("Web Search", key="formula_web_search_enabled"):
            st.info("Web search is enabled. Your queries will include relevant web information.")
        else:
            st.info("Web search is disabled.")
    
    with st.form("chat_input_form", clear_on_submit=False):
        initial_text = st.session_state.get("history_prompt", "")
        user_text = st.text_area("Type your message", value=initial_text)
        uploaded_file = st.file_uploader("Upload a PDF (optional)", type=["pdf"])
        force_ocr = st.checkbox("Force OCR (for scanned/image PDFs)", value=False)
        submit_button = st.form_submit_button("Send")
        if "history_prompt" in st.session_state:
            del st.session_state.history_prompt
    
    with top_container:
        status_placeholder = st.empty()
    
    if submit_button and (user_text or uploaded_file):
        with top_container:
            user_msg = {"text": user_text, "file": uploaded_file}
            # 여기서는 대화 기록을 sidebar의 딕셔너리 형식과 별도로 처리할 수 있음.
            # 예시로 st.session_state.chat_history에 append하지 않고, 주로 채팅 API와 저장함.
            if TEST_DEBUG_MODE:
                with st.chat_message("user"):
                    st.markdown(user_text)
                    if uploaded_file:
                        st.markdown("Uploaded PDF:")
                        st.write(uploaded_file.name)
            prompt = user_text
            extracted_text = ""
            if st.session_state.formula_web_search_enabled:
                prompt = enhance_prompt_with_web_search(prompt, True)
            
            col1, col2 = st.columns(2, gap="large")
            if uploaded_file:
                file_bytes = uploaded_file.read()
                with st.spinner("Parsing document...", show_time=True):
                    # process_document_with_upstage() 함수 구현 필요 (여기서는 placeholder)
                    extracted_text = "Parsed document text here..."
                if extracted_text:
                    prompt += f"\n\nAdditional context from document:\n{extracted_text}"
                    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
                    pdf_display = f"""
                    <embed 
                        src="data:application/pdf;base64,{base64_pdf}" 
                        width="700" 
                        height="1000" 
                        type="application/pdf">
                    """
                    with col1:
                        st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                status_placeholder.warning("No PDF uploaded, defaulting to prompt response.")
            
            with col2:
                st.subheader("🤖 Solar Response")
                with st.chat_message("assistant"):
                    # stream_response() 함수 구현 필요 (여기서는 단일 응답 사용)
                    response_text = "Assistant response generated here..."
                    st.markdown(response_text)
                    
                    messages = [
                        {"role": "user", "content": {"text": user_text, "file": uploaded_file.name if uploaded_file else None}},
                        {"role": "assistant", "content": response_text}
                    ]
                    save_conversation("document_processing", messages)
                    # 사용자 정보 추출 (예시)
                    # extract_user_info_from_document() 함수 구현 필요 (여기서는 placeholder)
                    user_info = None  
                    if user_info:
                        from utils import save_user_info
                        save_user_info(user_info)
    
    # --- Step 2: Form Validate ---
    with tab2:
        st.header("Step 2: Upload form for internal scan")
        top_container_2 = st.container()
        with st.form("pdf_edit_form", clear_on_submit=False):
            pdf_file_edit = st.file_uploader("Upload editted PDF file", type=["pdf"])
            submit_pdf_button = st.form_submit_button("Send PDF")
        if submit_pdf_button:
            with top_container_2:
                status_placeholder2 = st.empty()
                if pdf_file_edit is not None:
                    files = {"file": (pdf_file_edit.name, pdf_file_edit, "application/pdf")}
                    with st.spinner("Checking document...", show_time=True):
                        response = requests.post("http://localhost:8001/check-pdf", files=files)
                    if response.status_code == 200:
                        status_placeholder2.success("✅ Check complete.")
                    else:
                        status_placeholder2.error(f"Error: {response.status_code}")
                    pdf_file_edit.seek(0)
                    file_bytes_edit = pdf_file_edit.read()
                    base64_pdf_edit = base64.b64encode(file_bytes_edit).decode('utf-8')
                    pdf_display_edit = f"""
                        <embed 
                            src="data:application/pdf;base64,{base64_pdf_edit}" 
                            width="700" 
                            height="1000" 
                            type="application/pdf">
                    """
                    col1, col2 = st.columns(2, gap="medium")
                    with col1:
                        st.subheader("PDF Editor")
                        st.markdown(pdf_display_edit, unsafe_allow_html=True)
                    with col2:
                        st.subheader("Internal scan Response")
                        if response.status_code == 200:
                            st.json(response.json())
                        else:
                            status_placeholder2.error(response.text)
                else:
                    status_placeholder2.error("Please upload a file.")
