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
from chatbot_ui import init_chat_state, render_chat_button, render_chat_interface
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

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 페이지 설정
st.set_page_config(layout="wide")

# Initialize chat state and interface
init_chat_state()
render_chat_button()
render_chat_interface()

DEBUG_MODE = False
TEST_DEBUG_MODE = False

# Load Upstage API key
upstage_api_key = st.secrets.get("UPSTAGE_API_KEY") or os.getenv("UPSTAGE_API_KEY")

st.title("📄FORMula")

tab1, tab2 = st.tabs(["Step 1: Form Upload", "Step 2: Form Validate"])

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
        model_kwargs={"stream": True}
    )

    # Use `stream_raw` instead of __call__ to get the streaming generator
    stream = chat.stream([HumanMessage(content=prompt)])

    for chunk in stream:
        # Each chunk should be a ChatMessage — yield its content
        if hasattr(chunk, "content"):
            yield chunk.content

def extract_user_info_from_document(messages, extracted_text=""):
    """문서 처리 대화에서 사용자 정보를 추출합니다."""
    try:
        # 사용자 메시지와 문서 내용을 결합
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            return None
            
        # 사용자 정보 추출을 위한 프롬프트
        info_prompt = {
            "messages": [
                {"role": "system", "content": """You are an information extractor. Extract user information from the conversation and document.
                Look for information about:
                - Company name
                - Industry
                - Location
                - Contact information
                - Business type (importer/exporter)
                
                If you find any of these information, format it as a concise JSON object.
                If no information is found, return null.
                
                Only include fields that you are confident about.
                If a field's information is unclear or missing, omit it from the JSON."""},
                {"role": "user", "content": f"Extract user information from this conversation and document:\n\nConversation: {json.dumps(user_messages, ensure_ascii=False)}\n\nDocument content: {extracted_text}"}
            ]
        }
        
        response = requests.post(
            "http://localhost:8000/chat",
            json=info_prompt
        )
        
        if response.status_code == 200:
            try:
                # 응답을 JSON으로 파싱
                info = json.loads(response.json()["response"])
                if info:
                    info["timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S")
                    return info
            except:
                return None
        return None
    except Exception as e:
        print(f"Error extracting user info: {str(e)}")
        return None

def generate_user_info_description(info, extracted_text=""):
    """사용자 정보에 대한 설명을 생성합니다."""
    try:
        # 설명 생성을 위한 프롬프트
        description_prompt = {
            "messages": [
                {"role": "system", "content": """You are an information analyzer. Create a concise description of the user information.
                Include:
                1. Confidence level of the information
                2. Source of the information (conversation/document)
                3. Context and relevance
                4. Any potential uncertainties
                
                Format the response as a clear, professional description.
                Keep it concise but informative."""},
                {"role": "user", "content": f"Generate a description for this user information:\n\nInformation: {json.dumps(info, ensure_ascii=False)}\n\nDocument content: {extracted_text}"}
            ]
        }
        
        response = requests.post(
            "http://localhost:8000/chat",
            json=description_prompt
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        return None
    except Exception as e:
        print(f"Error generating description: {str(e)}")
        return None

def save_user_info(info, extracted_text=""):
    """사용자 정보를 저장합니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        if not os.path.exists(chat_history_dir):
            os.makedirs(chat_history_dir)
        
        user_info_file = os.path.join(chat_history_dir, "user_information.json")
        
        # 기존 정보 로드
        user_info = {}
        if os.path.exists(user_info_file):
            try:
                with open(user_info_file, "r", encoding="utf-8") as f:
                    user_info = json.load(f)
            except Exception as e:
                print(f"Error loading existing user info: {str(e)}")
                user_info = {}
        
        # 기존 정보가 없으면 새로운 정보로 초기화
        if "user_information" not in user_info:
            user_info["user_information"] = {}
        
        # 새로운 정보와 기존 정보 병합
        existing_info = user_info["user_information"]
        info_changed = False
        
        for key, value in info.items():
            if key != "timestamp":  # timestamp는 제외
                if key not in existing_info or existing_info[key] != value:
                    # 정보가 없거나 다른 경우에만 업데이트
                    existing_info[key] = value
                    info_changed = True
                    # 변경 이력 추가
                    if "update_history" not in existing_info:
                        existing_info["update_history"] = []
                    existing_info["update_history"].append({
                        "field": key,
                        "old_value": existing_info.get(key),
                        "new_value": value,
                        "timestamp": info["timestamp"]
                    })
        
        # 정보가 변경되었거나 설명이 없는 경우에만 새로운 설명 생성
        if info_changed or "description" not in existing_info:
            description = generate_user_info_description(existing_info, extracted_text)
            if description:
                existing_info["description"] = description
                if "update_history" not in existing_info:
                    existing_info["update_history"] = []
                existing_info["update_history"].append({
                    "field": "description",
                    "old_value": existing_info.get("description"),
                    "new_value": description,
                    "timestamp": info["timestamp"]
                })
        
        # 저장
        with open(user_info_file, "w", encoding="utf-8") as f:
            json.dump(user_info, f, ensure_ascii=False, indent=2)
        print(f"Successfully updated user information in: {user_info_file}")
    except Exception as e:
        print(f"Error saving user information: {str(e)}")

def generate_history_prompt(user_info):
    """사용자 정보를 기반으로 초기 프롬프트를 생성합니다."""
    if not user_info:
        return ""
        
    prompt = "Based on my previous information:\n\n"
    
    # 기본 정보 추가
    if "company_name" in user_info:
        prompt += f"Company: {user_info['company_name']}\n"
    if "industry" in user_info:
        prompt += f"Industry: {user_info['industry']}\n"
    if "location" in user_info:
        prompt += f"Location: {user_info['location']}\n"
    if "business_type" in user_info:
        prompt += f"Business Type: {user_info['business_type']}\n"
    
    # 설명 추가
    if "description" in user_info:
        prompt += f"\nContext: {user_info['description']}\n"
    
    prompt += "\nPlease help me with my trade and customs related questions."
    return prompt

# Initialize step
with tab1:
    st.header("Step 1: Input prompt with initial form")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_chat_history()

    top_container = st.container()

    # Fetch history and Web Search toggles
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        # Fetch history toggle
        if "fetch_history_toggle" not in st.session_state:
            st.session_state.fetch_history_toggle = False
            
        if st.toggle("Fetch my history", key="fetch_history_toggle"):
            if not st.session_state.get("history_loaded", False):
                user_info = load_user_info()
                if user_info:
                    history_prompt = generate_history_prompt(user_info)
                    st.session_state.history_prompt = history_prompt
                    st.session_state.history_loaded = True
                    st.success("History loaded successfully!")
                else:
                    st.warning("No previous history found.")
        else:
            st.session_state.history_loaded = False
    
    with col2:
        # Web search toggle
        if "formula_web_search_enabled" not in st.session_state:
            st.session_state.formula_web_search_enabled = False
            
        if st.toggle("Web Search", key="formula_web_search_enabled"):
            st.info("Web search is enabled. Your queries will automatically include relevant web information.")
        else:
            st.info("Web search is disabled.")

    with st.form("chat_input_form", clear_on_submit=False):
        # Initialize text area with history prompt if available
        initial_text = st.session_state.get("history_prompt", "")
        user_text = st.text_area("Type your message", value=initial_text)
        uploaded_file = st.file_uploader("Upload a PDF (optional)", type=["pdf"])
        force_ocr = st.checkbox("Force OCR (for scanned/image PDFs)", value=False)
        submit_button = st.form_submit_button("Send")
        
        # Clear prompts after first use
        if "history_prompt" in st.session_state:
            del st.session_state.history_prompt

    with top_container:
        status_placeholder = st.empty() 

    if submit_button and (user_text or uploaded_file):
        with top_container:
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
            
            # 웹 검색이 활성화된 경우 프롬프트 강화
            if st.session_state.formula_web_search_enabled:
                prompt = enhance_prompt_with_web_search(prompt, True)
            
            col1, col2 = st.columns(2, gap="large")

            # If PDF exists, extract and append context
            if uploaded_file:
                file_bytes = uploaded_file.read()

                with st.spinner("Parsing document...", show_time=True):
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
                    st.markdown(pdf_display, unsafe_allow_html=True)

            else:
                status_placeholder.warning("No PDF uploaded, defaulting to prompt response.")

            # Display assistant response
            with col2:
                st.subheader("🤖 Solar Response")
                with st.chat_message("assistant"):
                    response_stream = stream_response(prompt)
                    stream1, stream2 = itertools.tee(response_stream, 2)

                    st.write_stream(stream1)
                    response_text = ""
                    for chunk in stream2:
                        response_text += chunk
                        
                    
                    # 대화 저장
                    messages = [
                        {
                            "role": "user",
                            "content": {
                                "text": user_text,
                                "file": uploaded_file.name if uploaded_file else None
                            }
                        },
                        {
                            "role": "assistant",
                            "content": response_text
                        }
                    ]
                    save_conversation("document_processing", messages)
                    
                    # 사용자 정보 추출 및 저장
                    user_info = extract_user_info_from_document(messages, extracted_text)
                    if user_info:
                        save_user_info(user_info, extracted_text)

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

                with st.spinner("Checking document...", show_time=True):
                    response = requests.post("http://localhost:8001/check-pdf", files=files)

                if response.status_code == 200:
                    status_placeholder2.success("✅ Check complete.")
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
