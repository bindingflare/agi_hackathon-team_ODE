> 📢 **Notice:**  
> All teams submitting their project must create a README.md file following this guideline.  
> Please make sure to replace all placeholder texts (e.g., [Project Title], [Describe feature]) with actual content.

# 🛠️ FORMula - o1보다 강력한 Rag 기반 Form 작성 Agent

### 📌 Overview
This project was developed as part of the AGI Agent Application Hackathon. It aims to solve the common pain point of filling out complex forms and documents, especially when users are unsure of how to write them or what information is valid.

### 🚀 Key Features
- ✅ **Chatbot Service**:
   - Q&A on trade/customs-related topics.
   - Integrated web search.
   - Conversation history storage.
- ✅  **PDF Document Validation**:
   - Extract document information and compare with internal data.
   - Real-time information retrieval (via web search).
   - Other fixes.
- ✅ **Domain Knowledge: Trade & Customs Assistant**:
   - Check for regulatory compliance.
   - Inspection for hazardous substances/food additives.

### 🧩 Tech Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: VectorDB
- **Others**: Docker, LangChain, GPT-4o Search Preview, Upstage Embeddings API, Upstage Document Parsing API, Solar Pro

### 🏗️ Project Structure
```
📁 agi_hackathon-team_ODE/
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

### 🔧 Setup & Installation

```bash
# Clone the repository
git clone https://github.com/bindingflare/agi_hackathon-team_ODE/
cd agi_hackathon-team_ODE
```

```bash
# Copy zip file to ./Database (Keep file structure intact!)
```

```bash
# Set API Keys (.env)
./Chatbot/.env
UPSTAGE_API_KEY = "your_api_key"
UPSTAGE_EMBEDDING_KEY = "your_api_key"

./PDFValidator/.env
UPSTAGE_API_KEY = "your_api_key"

./Streamlit/.env
UPSTAGE_API_KEY = "your_api_key"
OPENAI_API_KEY = "your_api_key"
```

```bash
# Run with Docker Compose
# Run with Docker Compose
docker-compose up -d
```

```bash
# Access Streamlit UI
http://localhost:8501
```

### 📁 Dataset & References
- **Dataset used**: [source and brief explanation]
- **References / Resources**:  
  [link 1]  
  [link 2]

### 🙌 Team Members

| Name   | Role   | Github                     |
|--------|--------|---------------------------|
| 방준현 | Team Lead  | [@bindingflare](https://github.com/bindingflare)         |
| 손재훈 | Backend    | [@wognsths](https://github.com/wognsths)   |
| 이재영 | Modelling  | [@sleepylee02](https://github.com/sleepylee02)   |
| 윤희찬 | Backend, Modelling    | [@quant-jason](https://github.com/quant-jason)   |
| 김정인 | Front-End    | [@jungin7612](https://github.com/jungin7612)   |

### ⏰ Development Period
- Last updated: 2025-04-04

### 📄 License
This project is licensed under the [MIT license](https://opensource.org/licenses/MIT).  
See the LICENSE file for more details.

### 💬 Additional Notes
- Feel free to include any other relevant notes or links here.


