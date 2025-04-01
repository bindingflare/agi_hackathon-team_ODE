# agi_hackathon-team_ODE

### 간단 파일구조 구현

```md
export_rag_bot/
├── app/
│   ├── [main.py](http://main.py/)                  # FastAPI 서버 진입점
│   ├── api/
│   │   └── [endpoints.py](http://endpoints.py/)         # API 라우팅 (chat, health 등)
│   ├── core/
│   │   ├── [config.py](http://config.py/)            # 설정 정보 (env, model path 등)
│   │   └── [pipeline.py](http://pipeline.py/)          # RAG 추론 파이프라인 정의
│   ├── db/
│   │   ├── [loader.py](http://loader.py/)            # 다양한 문서 DB 로딩 및 벡터화
│   │   ├── vector_store.py      # FAISS, Chroma, Weaviate 등 연결
│   │   └── sources/
│   │       ├── customs_cases/   # 통관 문제사례
│   │       ├── additives/       # 식품첨가물 규정
│   │       ├── hazardous/       # 유해물질 규정
│   │       ├── forms/           # 제출 서류 양식
│   │       ├── reports/         # 국가별 보고서 및 주의사항
│   │       └── market/          # 증권 리포트 등
│   ├── models/
│   │   ├── rag_model.py         # LLM + Retriever 결합 모델 정의
│   │   └── [embedder.py](http://embedder.py/)          # 임베딩 모델 (e.g., SBERT, KoSimCSE)
│   └── utils/
│       ├── [parser.py](http://parser.py/)            # PDF / Excel / HTML 등 파서 유틸
│       └── [logger.py](http://logger.py/)            # 로그 설정
├── tools/                    # Agent가 호출할 수 있는 함수 정의
│   ├── search_documents.py   # 문서 검색 함수
│   ├── get_required_forms.py # 필요한 수출 서류 검색 함수
│   ├── check_regulations.py  # 식품첨가물/유해물질 규정 확인
│   └── **init**.py
├── data/                        # 원본 데이터 (마운트용 or 초기 적재용)
├── Dockerfile                   # 컨테이너 설정
├── requirements.txt             # 의존성 목록
├── .env                         # 환경변수 설정
└── [README.md](http://readme.md/)                    # 프로젝트 설명
```

### ENV format

