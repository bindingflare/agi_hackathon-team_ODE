import json
import os
from datetime import datetime
import tempfile
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key="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")

def get_conversation_file_path(conversation_type: str):
    """대화 유형별 파일 경로를 반환합니다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_names = {
        "sidebar_chat": "trade_chat_memory.json",
        "document_processing": "document_memory.json",
        "pdf_validation": "form_memory.json"
    }
    return os.path.join(current_dir, file_names.get(conversation_type, "conversation_memory.json"))

def save_conversation(conversation_type: str, messages: list):
    """
    대화 내용을 각 도우미별 파일에 저장합니다.
    
    Args:
        conversation_type (str): 대화 유형 ('sidebar_chat', 'document_processing', 'pdf_validation')
        messages (list): 대화 메시지 목록
    """
    try:
        file_path = get_conversation_file_path(conversation_type)
        
        # 파일이 존재하면 읽기, 없으면 빈 딕셔너리 생성
        memory = {"conversations": []}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        memory = json.load(f)
                        if not isinstance(memory, dict) or "conversations" not in memory:
                            print(f"파일 형식이 올바르지 않습니다. 초기화합니다: {file_path}")
                            memory = {"conversations": []}
                    except json.JSONDecodeError:
                        print(f"JSON 파싱 오류가 발생했습니다. 파일을 초기화합니다: {file_path}")
                        memory = {"conversations": []}
            except Exception as e:
                print(f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")
                print(f"새로 시작합니다: {file_path}")
                memory = {"conversations": []}

        # 현재 시간을 키로 사용
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 대화 내용에 시간 정보 추가
        conversation_data = {
            "timestamp": current_time,
            "messages": messages
        }
        
        # 대화 내용 추가
        memory["conversations"].append(conversation_data)
        
        # 시간순으로 정렬
        memory["conversations"].sort(key=lambda x: x["timestamp"])

        # 임시 파일에 먼저 저장
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path), suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
            
            # 임시 파일을 실제 파일로 이동
            if os.path.exists(file_path):
                os.replace(temp_path, file_path)
            else:
                os.rename(temp_path, file_path)
                
            print(f"대화가 저장되었습니다: {file_path}")
            
        except Exception as e:
            os.unlink(temp_path)
            raise e
            
    except Exception as e:
        print(f"대화 저장 중 오류 발생: {str(e)}")

def load_conversations(conversation_type: str = None):
    """
    저장된 대화 내용을 불러옵니다.
    
    Args:
        conversation_type (str, optional): 특정 대화 유형만 불러올 경우 지정
        
    Returns:
        dict: 저장된 대화 내용
    """
    try:
        file_path = get_conversation_file_path(conversation_type)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                return memory.get("conversations", [])
        return []
    except Exception as e:
        print(f"대화 불러오기 중 오류 발생: {str(e)}")
        return []

def perform_web_search(query):
    """웹 검색을 수행하고 결과를 저장합니다."""
    try:
        # 웹 검색을 위한 프롬프트 생성
        search_prompt = f"""Please search the web for information about: {query}
        Provide a comprehensive summary of the findings, including:
        1. Key facts and details
        2. Relevant sources
        3. Any important context or background
        Format the response in a clear, structured way."""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful web search assistant. Provide accurate and relevant information from the web."},
                {"role": "user", "content": search_prompt}
            ]
        )
        
        search_result = response.choices[0].message.content
        
        # 검색 결과 저장
        save_search_result(query, search_result)
        
        return search_result
    except Exception as e:
        print(f"Error performing web search: {str(e)}")
        return None

def enhance_prompt_with_web_search(prompt, web_search_enabled=False):
    """프롬프트에 웹 검색 결과를 통합합니다."""
    if not web_search_enabled:
        return prompt
        
    try:
        # 웹 검색 수행
        search_result = perform_web_search(prompt)
        if search_result:
            # 검색 결과를 프롬프트에 통합
            enhanced_prompt = f"""Based on the following web search results:

{search_result}

Please provide a comprehensive response to this query: {prompt}

Make sure to incorporate relevant information from the web search results while maintaining accuracy and relevance."""
            return enhanced_prompt
    except Exception as e:
        print(f"Error enhancing prompt with web search: {str(e)}")
    
    return prompt

def save_search_result(query, result):
    """검색 결과를 저장합니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        if not os.path.exists(chat_history_dir):
            os.makedirs(chat_history_dir)
        
        search_file = os.path.join(chat_history_dir, "search_history.json")
        
        # 기존 검색 기록 로드
        search_history = {}
        if os.path.exists(search_file):
            try:
                with open(search_file, "r", encoding="utf-8") as f:
                    search_history = json.load(f)
            except Exception as e:
                print(f"Error loading search history: {str(e)}")
                search_history = {}
        
        # 새로운 검색 결과 추가
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = f"search_{timestamp}"
        
        search_history[search_id] = {
            "query": query,
            "result": result,
            "timestamp": timestamp
        }
        
        # 저장
        with open(search_file, "w", encoding="utf-8") as f:
            json.dump(search_history, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved search result to: {search_file}")
    except Exception as e:
        print(f"Error saving search result: {str(e)}")

def load_search_history():
    """저장된 검색 기록을 불러옵니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        search_file = os.path.join(chat_history_dir, "search_history.json")
        
        if not os.path.exists(search_file):
            return {}
        
        with open(search_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            return history
    except Exception as e:
        print(f"Error loading search history: {str(e)}")
        return {}

def load_user_info():
    """저장된 사용자 정보를 불러옵니다."""
    try:
        chat_history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        user_info_file = os.path.join(chat_history_dir, "user_information.json")
        
        if not os.path.exists(user_info_file):
            return None
        
        with open(user_info_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("user_information")
    except Exception as e:
        print(f"Error loading user information: {str(e)}")
        return None 