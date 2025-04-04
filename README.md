# FORMulator - Trade & Customs Assistant

The world's simplest and most powerful form-filling agent  
This repository is specialized in intelligent responses related to trade (K-FOOD exports) and customs inquiries.

## Project Structure

```
agi_hackathon-team_ODE/
├── Chatbot/                    # Chatbot backend server
│   ├── main.py                # FastAPI server implementation
│   ├── requirements.txt       # Backend dependencies
│   ├── .env                   # Environment variable settings
│   ├── vector_db/             # Vector database storage
│   ├── data/                  # Data storage
│   └── base_knowledge_memory.json  # Basic knowledge storage
│
├── Streamlit/                 # Frontend web interface
│   ├── main.py                # Main Streamlit app
│   ├── pdf_form.py            # PDF form-related features
│   ├── sidebar.py             # Sidebar UI components
│   ├── utils.py               # Utility functions
│   ├── requirements.txt       # Frontend dependencies
│   ├── .env                   # Environment variable settings
│   ├── data/                  # Data storage
│   └── .streamlit/            # Streamlit configuration
│
├── PDFValidator/              # PDF document validation service
│   ├── main.py                # FastAPI server
│   ├── requirements.txt       # PDF validation dependencies
│   ├── .env                   # Environment variable settings
│   ├── data/                  # Data storage
│   └── memory.json            # Memory storage
│
├── Database/                  # Database-related files
│   ├── Merged/                # Merged data
│   ├── Embedding/             # Embedding data
│   └── Connection/            # Database connection
│
├── .devcontainer/             # Development container configuration
├── docker-compose.yaml        # Docker Compose configuration
└── README.md                  # Project documentation
```

## Key Features

1. **Chatbot Service**
   - Q&A on trade/customs-related topics
   - Integrated web search
   - Conversation history storage

2. **PDF Document Validation**
   - Extract document information and compare with internal data
   - Check for regulatory compliance
   - Inspection for hazardous substances/food additives
   - Other fixes

3. **Database Integration**
   - Use of vector database
   - Real-time information retrieval (via Web Search API)

## Installation & Execution

1. Git Clone
```bash
# Clone the repository
git clone [repository_url]
cd agi_hackathon-team_ODE
```

2. Set API Keys (.env)
```
./Chatbot/.env
UPSTAGE_API_KEY = "your_api_key"
UPSTAGE_EMBEDDING_KEY = "your_api_key"

./PDFValidator/.env
UPSTAGE_API_KEY = "your_api_key"

./Streamlit/.env
UPSTAGE_API_KEY = "your_api_key"
OPENAI_API_KEY = "your_api_key"
```

3. Run with Docker Compose
```bash
# Run with Docker Compose
docker-compose up -d
```

4. Access
- Streamlit UI: http://localhost:8501

## Team Members

| Name   | Role   | Email                     |
|--------|--------|---------------------------|
| 방준현 | Team Lead | junhb@yonsei.ac.kr         |
| 손재훈 | Member    | 2021122006@yonsei.ac.kr   |
| 이재영 | Member    | jaeyoung02@yonsei.ac.kr   |
| 윤희찬 | Member    | jason0295@yonsei.ac.kr    |
| 김정인 | Member    | jungin0210@yonsei.ac.kr   |
