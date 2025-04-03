import streamlit as st
import requests
import json
from datetime import datetime
import os
from utils import (
    save_conversation, 
    load_conversations, 
    perform_web_search, 
    save_search_result, 
    load_search_history,
    enhance_prompt_with_web_search
)

def load_chat_history():
    try:
        chat_history_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../Chatbot/chat_history"
        )
        history_file = os.path.join(chat_history_dir, "chat_history.json")

        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                chat_history = json.load(f)
            return chat_history
        else:
            return {}
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return {}
    
# 세션 초기화: 딕셔너리 형식으로 채팅 기록을 로드
st.session_state.show_chat = st.session_state.get("show_chat", False)
st.session_state.chat_messages = st.session_state.get("chat_messages", [])
st.session_state.current_chat_id = st.session_state.get("current_chat_id", None)
st.session_state.chat_history = st.session_state.get("chat_history", load_chat_history())
st.session_state.web_search_enabled = st.session_state.get("web_search_enabled", False)

def create_new_chat():
    """새로운 채팅을 생성합니다."""
    try:
        chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_chat = {
            "id": chat_id,
            "messages": [],
            "title": "New Chat",
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        st.session_state.chat_history[chat_id] = new_chat
        st.session_state.current_chat_id = chat_id
        st.session_state.chat_messages = []
        print(f"Created new chat with ID: {chat_id}")
    except Exception as e:
        print(f"Error creating new chat: {str(e)}")

def generate_chat_title(messages):
    try:
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            return "New Chat"
        first_message = user_messages[0]["content"]
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a title generator. Create a very short title (max 3 words) for the following conversation."
                    },
                    {
                        "role": "user", 
                        "content": f"Generate a very short title for this conversation: {first_message}"
                    }
                ]
            }
        )
        if response.status_code == 200:
            title = response.json()["response"].strip()
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
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            return None
        info_prompt = {
            "messages": [
                {"role": "system", "content": "You are an information extractor. Extract user information from the conversation."},
                {"role": "user", "content": f"Extract info from: {json.dumps(user_messages, ensure_ascii=False)}"}
            ]
        }
        response = requests.post("http://localhost:8000/chat", json=info_prompt)
        if response.status_code == 200:
            try:
                info = json.loads(response.json()["response"])
                if info:
                    info["timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S")
                    return info
            except Exception as e:
                return None
        return None
    except Exception as e:
        print(f"Error extracting user info: {str(e)}")
        return None

def save_user_info(info):
    """사용자 정보를 저장합니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../Chatbot/chat_history")
        if not os.path.exists(chat_history_dir):
            os.makedirs(chat_history_dir)
        user_info_file = os.path.join(chat_history_dir, "user_information.json")
        user_info = {}
        if os.path.exists(user_info_file):
            try:
                with open(user_info_file, "r", encoding="utf-8") as f:
                    user_info = json.load(f)
            except Exception as e:
                print(f"Error loading existing user info: {str(e)}")
                user_info = {}
        user_info["user_information"] = info
        with open(user_info_file, "w", encoding="utf-8") as f:
            json.dump(user_info, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved user information to: {user_info_file}")
    except Exception as e:
        print(f"Error saving user information: {str(e)}")

def init_chat_state():
    """채팅 상태를 초기화합니다."""
    st.session_state.show_chat = st.session_state.get("show_chat", False)
    st.session_state.chat_messages = st.session_state.get("chat_messages", [])
    st.session_state.current_chat_id = st.session_state.get("current_chat_id", None)
    st.session_state.chat_history = load_chat_history()
    st.session_state.web_search_enabled = st.session_state.get("web_search_enabled", False)

def render_chat_button():
    """채팅 버튼을 렌더링합니다."""
    if not st.session_state.show_chat:
        if st.sidebar.button("+ Chatbot"):
            st.session_state.show_chat = True
            create_new_chat()
            st.rerun()
    else:
        # 채팅이 활성화된 경우에만 Web Search 체크박스 표시
        if st.sidebar.checkbox("Web Search", key="chatbot_web_search_enabled"):
            st.sidebar.info("Web search is enabled. Your queries will include relevant web information.")
        else:
            st.sidebar.info("Web search is disabled.")

def render_chat_interface():
    """채팅 인터페이스를 렌더링합니다."""
    if st.session_state.show_chat:
        chat_sidebar = st.sidebar.container()
        with chat_sidebar:
            st.title("Trade & Customs Assistant")
            if st.button("New Chat", key="new_chat_sidebar"):
                st.session_state.chat_messages = []
                st.session_state.current_chat_id = None
                st.rerun()
            st.subheader("Chat History")
            for chat in st.session_state.chat_history.values():
                title = chat.get("title", "New Chat")
                if st.button(title, key=f"chat_{chat['id']}"):
                    st.session_state.current_chat_id = chat["id"]
                    st.session_state.chat_messages = chat.get("messages", [])
                    st.rerun()
            if not st.session_state.chat_messages:
                st.info("Welcome! How can I assist you today?")
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            if prompt := st.chat_input("Ask about trade & customs"):
                if st.session_state.web_search_enabled:
                    prompt = enhance_prompt_with_web_search(prompt, True)
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                try:
                    response = requests.post("http://localhost:8000/chat", json={"messages": st.session_state.chat_messages})
                    if response.status_code == 200:
                        bot_message = response.json()["response"]
                        st.session_state.chat_messages.append({"role": "assistant", "content": bot_message})
                        if len(st.session_state.chat_messages) == 2:
                            title = generate_chat_title(st.session_state.chat_messages)
                            for key, chat in st.session_state.chat_history.items():
                                if chat["id"] == st.session_state.current_chat_id:
                                    chat["title"] = title
                                    st.session_state.chat_history[key] = chat
                                    break
                        user_info = extract_user_info(st.session_state.chat_messages)
                        if user_info:
                            save_user_info(user_info)
                    else:
                        error_message = f"Error: {response.status_code}"
                        st.session_state.chat_messages.append({"role": "assistant", "content": error_message})
                    if st.session_state.current_chat_id:
                        for key, chat in st.session_state.chat_history.items():
                            if chat["id"] == st.session_state.current_chat_id:
                                chat["messages"] = st.session_state.chat_messages
                                from utils import save_conversation
                                # 전체 대화 데이터를 chat 딕셔너리로 전달합니다.
                                save_conversation("sidebar_chat", chat)
                                st.session_state.chat_history[key] = chat
                                break
                    st.rerun()
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_message})
                    st.rerun()


def main():
    init_chat_state()
    render_chat_button()
    render_chat_interface()

if __name__ == "__main__":
    main()
