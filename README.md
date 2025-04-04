# FORMulator - Trade & Customs Assistant

세상에서 가장 간단하고 강력한 Form 작성 Agent
현재 레포는 무역 및 통관 관련 문의에 대한 지능형 응답에 특화된 시스템입니다.

## 프로젝트 구조

```
agi_hackathon-team_ODE/
├── Chatbot/                    # 챗봇 백엔드 서버
│   ├── main.py                # FastAPI 서버 구현
│   ├── requirements.txt       # 백엔드 의존성
│   ├── vector_db/            # 벡터 데이터베이스 저장소
│   └── chat_history/         # 채팅 기록 저장소
│
├── Streamlit/                 # 프론트엔드 웹 인터페이스
│   ├── main.py               # 메인 Streamlit 앱
│   ├── sidebar.py            # 사이드바 UI 컴포넌트
│   ├── utils.py              # 유틸리티 함수들
│   ├── requirements.txt      # 프론트엔드 의존성
│   └── .streamlit/          # Streamlit 설정
│       ├── config.toml
│       └── secrets.toml     # API 키 설정
│
├── PDFValidator/             # PDF 문서 검증 서비스
│   ├── main.py              # FastAPI 서버
│   └── requirements.txt     # PDF 검증 의존성
│
├── Database/                 # 데이터베이스 관련 파일
│   └── data/               # 원본 데이터 저장소
│
├── docker-compose.yaml       # 도커 컴포즈 설정
├── requirements.txt         # 공통 의존성
└── README.md               # 프로젝트 문서
```

## 주요 기능

1. **챗봇 서비스**
   - 무역/통관 관련 질의응답
   - 웹 검색 기능 통합
   - 대화 기록 저장 및 관리

2. **PDF 문서 검증**
   - 문서 정보 추출
   - 규정 준수 여부 확인
   - 유해물질/식품첨가물 검사

3. **데이터베이스 통합**
   - 벡터 데이터베이스 활용
   - 실시간 정보 검색
   - 규정/법률 정보 저장

## 설치 및 실행

1. 환경 설정
```bash
# 저장소 클론
git clone [repository_url]
cd agi_hackathon-team_ODE

# 도커 컴포즈로 실행
docker-compose up -d
```

2. API 키 설정
```
UPSTAGE_API_KEY = "your_api_key"
EMBEDDING_API_KEY
OPENAI_KEY
```

3. 접속
- Streamlit UI: http://localhost:8501
- FastAPI 서버: http://localhost:8000
- PDF 검증 서비스: http://localhost:8002

## 팀 소개

| 이름   | 역할   | 이메일                     |
|--------|--------|----------------------------|
| 방준현 | 팀장   | junhb@yonsei.ac.kr         |
| 손재훈 | 팀원   | 2021122006@yonsei.ac.kr   |
| 이재영 | 팀원   | jaeyoung02@yonsei.ac.kr   |
| 윤희찬 | 팀원   | jason0295@yonsei.ac.kr    |
| 김정인 | 팀원   | jungin0210@yonsei.ac.kr   |
