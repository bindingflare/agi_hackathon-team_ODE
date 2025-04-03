import os
import json
import re
from typing import List
from fastapi import BackgroundTasks, FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

def entity_processor_record(record: dict, record_key: str) -> List[dict]:
    result_list = []
    link_pattern = r'\(\[[^\]]+\]\([^)]+\)\)'
    result_text = record.get('result', '')
    
    # 마크다운 링크 패턴을 기준으로 텍스트 분리
    segments = re.split(link_pattern, result_text)
    segments = [seg.strip() for seg in segments if seg.strip()]
    
    # 각 텍스트 세그먼트를 순서대로 변환
    for index, segment in enumerate(segments):
        d = {
            "id": 0,  # 누적 id로 업데이트됨
            "page": index + 1,  # 기록 내 페이지 번호
            "text": segment,
            "source_file": record_key,
            "category": "paragraph"
        }
        result_list.append(d)
    return result_list

def load_json_file(filepath: str):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json_file(filepath: str, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def process_chat_history():
    # 파일 경로 설정
    chat_history_path = os.path.join("../Chatbot/chat_history/search_history.json")
    cumulative_path = os.path.join("..", "Database", "Merged", "merged_documents.json")
    processed_keys_path = "processed_keys.json"
    
    # 기존 파일 로드
    chat_history = load_json_file(chat_history_path)
    cumulative_data = load_json_file(cumulative_path)
    if not isinstance(cumulative_data, list):
        cumulative_data = []
    processed_keys = load_json_file(processed_keys_path)
    if not isinstance(processed_keys, list):
        processed_keys = []
    
    # 누적 데이터에서 현재 최대 id 획득 (기본값은 0)
    current_max_id = max((item.get("id", 0) for item in cumulative_data), default=0)
    
    # 아직 처리되지 않은 채팅 기록 처리
    for key, record in chat_history.items():
        if key in processed_keys:
            continue  # 이미 처리된 항목은 건너뜀
        new_segments = entity_processor_record(record, key)
        # 각 세그먼트에 누적 id 할당
        for seg in new_segments:
            current_max_id += 1
            seg["id"] = current_max_id
        cumulative_data.extend(new_segments)
        processed_keys.append(key)
    
    # 업데이트된 결과와 처리된 키 저장
    save_json_file(cumulative_path, cumulative_data)
    save_json_file(processed_keys_path, processed_keys)
    print("Chat history processing completed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 scheduler 생성 및 작업 등록
    scheduler = AsyncIOScheduler()
    # 예: 60초마다 process_chat_history 실행
    scheduler.add_job(process_chat_history, 'interval', seconds=60)
    scheduler.start()
    print("Scheduler started")
    yield
    # 서버 종료 시 scheduler shutdown
    scheduler.shutdown()
    print("Scheduler shutdown")

app = FastAPI(lifespan=lifespan)

@app.post("/process")
async def process_endpoint(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_chat_history)
    return {"message": "Chat history processing is running in the background."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
