from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from langchain_upstage import ChatUpstage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os
import json
import asyncio

app = FastAPI()

# UPSTAGE API 설정
os.environ["UPSTAGE_API_KEY"] = "up_LYEjt0aGQV2SPaH22Mos5CqAzbikF"
chat = ChatUpstage(api_key=os.environ["UPSTAGE_API_KEY"], model="solar-pro")

# 무역 관련 메모리 데이터 로드
with open("memory.json", "r", encoding="utf-8") as f:
    memory_data = json.load(f)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

async def get_trade_response(messages: List[ChatMessage]) -> str:
    # LangChain 메시지 형식으로 변환
    langchain_messages = [
        SystemMessage(content=f"""You are a specialized Trade and Customs Assistant. 
        You have expertise in international trade procedures, HS codes,
        customs documentation, and regulations.
        
        Use the following trade knowledge base for accurate responses:
        {json.dumps(memory_data, ensure_ascii=False)}
        
        Always provide accurate and helpful information about these topics.""")
    ]
    
    # 사용자 메시지 추가
    for msg in messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    
    # UPSTAGE 모델로 응답 생성
    response = await chat.ainvoke(langchain_messages)
    
    return response.content

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response = await get_trade_response(request.messages)
        return ChatResponse(response=response)
    except Exception as e:
        return ChatResponse(response=f"Error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 