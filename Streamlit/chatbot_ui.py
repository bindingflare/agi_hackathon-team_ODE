import streamlit as st
import requests
import json
from datetime import datetime
import os
from typing import List
from utils import save_conversation, load_conversations, perform_web_search, save_search_result, load_search_history

# 세션 상태 초기화
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

def save_conversation(chat_id, messages, title=None):
    """대화 내용을 저장합니다."""
    try:
        # 절대 경로로 chat_history 디렉토리 생성
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        if not os.path.exists(chat_history_dir):
            os.makedirs(chat_history_dir)
            print(f"Created chat_history directory at: {chat_history_dir}")
        
        # 모든 채팅 기록을 저장할 파일
        history_file = os.path.join(chat_history_dir, "chat_history.json")
        
        # 기존 기록 로드
        chat_history = {}
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    chat_history = json.load(f)
            except Exception as e:
                print(f"Error loading existing chat history: {str(e)}")
                chat_history = {}
        
        # 새로운 채팅 추가
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_history[chat_id] = {
            "messages": messages,
            "title": title,
            "timestamp": timestamp
        }
        
        # 전체 기록 저장
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved chat to history file: {history_file}")
    except Exception as e:
        print(f"Error saving chat: {str(e)}")

def load_chat_history():
    """저장된 채팅 기록을 불러옵니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        history_file = os.path.join(chat_history_dir, "chat_history.json")
        
        if not os.path.exists(history_file):
            print(f"Chat history file not found at: {history_file}")
            return {}
        
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            print(f"Successfully loaded chat history from: {history_file}")
            return history
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return {}

def create_new_chat():
    """새로운 채팅을 생성합니다."""
    chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_messages = []
    st.session_state.chat_history[chat_id] = {"messages": [], "title": "New Chat"}
    return chat_id

def generate_chat_title(messages):
    """AI를 사용하여 채팅 제목을 생성합니다."""
    try:
        # 첫 번째 사용자 메시지를 기반으로 제목 생성
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            return "New Chat"
            
        first_message = user_messages[0]["content"]
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": [
                    {"role": "system", "content": "You are a title generator. Create a very short title (maximum 3 words) for the following conversation. The title should be descriptive but concise. Respond with only the title, nothing else."},
                    {"role": "user", "content": f"Generate a very short title (max 3 words) for this conversation: {first_message}"}
                ]
            }
        )
        
        if response.status_code == 200:
            title = response.json()["response"].strip()
            # 3단어로 제한
            words = title.split()
            if len(words) > 3:
                title = " ".join(words[:3]) + "..."
            return title
        return "New Chat"
    except Exception as e:
        print(f"Error generating title: {str(e)}")
        return "New Chat"

def extract_user_info(messages):
    """대화 내용에서 사용자 정보를 추출합니다."""
    try:
        # 사용자 메시지만 필터링
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            return None
            
        # 사용자 정보 추출을 위한 프롬프트
        info_prompt = {
            "messages": [
                {"role": "system", "content": """You are an information extractor. Extract user information from the conversation.
                Look for information about:
                - Company name
                - Industry
                - Location
                - Contact information
                - Business type (importer/exporter)
                
                If you find any of these information, format it as a concise JSON object.
                If no information is found, return null."""},
                {"role": "user", "content": f"Extract user information from this conversation: {json.dumps(user_messages, ensure_ascii=False)}"}
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

def save_user_info(info):
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
        
        # 새로운 정보 추가
        user_info["user_information"] = info
        
        # 저장
        with open(user_info_file, "w", encoding="utf-8") as f:
            json.dump(user_info, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved user information to: {user_info_file}")
    except Exception as e:
        print(f"Error saving user information: {str(e)}")

def init_chat_state():
    """채팅 상태를 초기화합니다."""
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_chat_history()  # 시작할 때 저장된 채팅 히스토리 로드
        print(f"Loaded chat history: {st.session_state.chat_history}")
    if "web_search_enabled" not in st.session_state:
        st.session_state.web_search_enabled = False

def render_chat_button():
    """채팅 버튼을 렌더링합니다."""
    if not st.session_state.show_chat:
        if st.sidebar.button("+ Chatbot"):
            st.session_state.show_chat = True
            create_new_chat()
            st.rerun()

    # Web search toggle in sidebar
    if st.sidebar.toggle("Web Search", key="chatbot_web_search_enabled"):
        st.sidebar.info("Web search is enabled. Your queries will automatically include relevant web information.")
    else:
        st.sidebar.info("Web search is disabled.")

def render_chat_interface():
    """채팅 인터페이스를 렌더링합니다."""
    if st.session_state.show_chat:
        chat_sidebar = st.sidebar.container()
        
        with chat_sidebar:
            st.title("Trade & Customs Assistant")
            
            # New Chat 버튼을 사이드바 상단에 배치
            if st.button("New Chat", key="new_chat_sidebar"):
                st.session_state.messages = []
                st.session_state.current_chat_id = None
                st.rerun()
            
            # 채팅 목록 표시
            st.subheader("Chat History")
            for chat_id, chat_data in st.session_state.chat_history.items():
                title = chat_data.get("title", "New Chat")
                if st.button(title, key=f"chat_{chat_id}"):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.chat_messages = chat_data.get("messages", [])
                    st.rerun()
            
            # Help message
            if not st.session_state.chat_messages:
                st.info("""Welcome! I can help you with:
                - HS Code information
                - Incoterms explanations
                - Import/Export procedures
                - Required documentation
                
                How can I assist you today?""")
            
            # Display chat messages
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # User input
            if prompt := st.chat_input("Ask about trade & customs"):
                # 웹 검색이 활성화된 경우 프롬프트 강화
                if st.session_state.web_search_enabled:
                    prompt = enhance_prompt_with_web_search(prompt, True)
                
                # Add user message
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                
                # API request
                try:
                    response = requests.post(
                        "http://localhost:8000/chat",
                        json={
                            "messages": st.session_state.chat_messages
                        }
                    )
                    if response.status_code == 200:
                        bot_message = response.json()["response"]
                        # Add bot response
                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": bot_message}
                        )
                        
                        # 첫 메시지가 추가될 때 제목 생성
                        if len(st.session_state.chat_messages) == 2:  # 첫 번째 대화가 완료될 때
                            title = generate_chat_title(st.session_state.chat_messages)
                            if st.session_state.current_chat_id:
                                st.session_state.chat_history[st.session_state.current_chat_id]["title"] = title
                                
                        # 사용자 정보 추출 및 저장
                        user_info = extract_user_info(st.session_state.chat_messages)
                        if user_info:
                            save_user_info(user_info)
                    else:
                        error_message = f"Error: {response.status_code}"
                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": error_message}
                        )
                    
                    # 현재 채팅 저장
                    if st.session_state.current_chat_id:
                        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.chat_messages
                        save_conversation(
                            st.session_state.current_chat_id, 
                            st.session_state.chat_messages,
                            st.session_state.chat_history[st.session_state.current_chat_id].get("title")
                        )
                    
                    # Refresh screen
                    st.rerun()
                    
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": error_message}
                    )
                    # 에러 발생시에도 대화 저장
                    if st.session_state.current_chat_id:
                        st.session_state.chat_history[st.session_state.current_chat_id]["messages"] = st.session_state.chat_messages
                        save_conversation(
                            st.session_state.current_chat_id, 
                            st.session_state.chat_messages,
                            st.session_state.chat_history[st.session_state.current_chat_id].get("title")
                        )
                    st.rerun()
            
            # Control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reset Chat", on_click=lambda: st.session_state.update({"chat_messages": []}), use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("Close Assistant", on_click=lambda: st.session_state.update({"show_chat": False}), use_container_width=True):
                    st.rerun()

def main():
    """채팅 인터페이스를 초기화하고 렌더링합니다."""
    init_chat_state()
    render_chat_button()
    render_chat_interface()

if __name__ == "__main__":
    main() 