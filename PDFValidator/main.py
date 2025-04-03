from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from langchain_upstage import ChatUpstage, UpstageDocumentParseLoader
from langchain_core.messages import HumanMessage
import os, json, tempfile
import pandas as pd
from datetime import datetime

app = FastAPI()
os.environ["UPSTAGE_API_KEY"] = "up_LYEjt0aGQV2SPaH22Mos5CqAzbikF"
chat = ChatUpstage(api_key=os.environ["UPSTAGE_API_KEY"], model="solar-pro")

# 메모리 기준 데이터
with open("memory.json", "r", encoding="utf-8") as f:
    memory_data = json.load(f)

# "준비된" CSV 로딩 (각각 combined_text 열이 있음)
harmful_df = pd.read_csv("harmful_substances_prepared.csv")  # 유해물질
additives_df = pd.read_csv("food_additives_prepared.csv")     # 식품첨가물
customs_df = pd.read_csv("customs_issues_prepared.csv")       # 통관 문제

def filter_df_prepared(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """combined_text 열에서 keywords 중 1개 이상 포함되면 필터링"""
    mask = df["combined_text"].apply(
        lambda val: sum(kw in str(val) for kw in keywords) >= 1
    )
    return df[mask]

def get_conversation_file_path():
    """conversation_memory.json 파일의 절대 경로를 반환합니다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, "conversation_memory.json")

@app.post("/check-pdf")
async def check_pdf(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # 1. PDF 파싱
        loader = UpstageDocumentParseLoader(tmp_path, ocr="force")
        pages = loader.load()
        parsed_text = "\n".join([p.page_content for p in pages])

        # 2. 기준값 비교 프롬프트
        prompt_compare = f"""
아래는 문서에서 파싱된 데이터입니다:

{parsed_text}

그리고 내부 시스템에 저장된 기준값은 다음과 같습니다:

{json.dumps(memory_data, ensure_ascii=False, indent=2)}

문서 내 데이터가 메모리 기준값과 일치하는지 확인하고, 불일치하거나 문제가 되는 부분이 있으면 모두 상세히 지적해주세요.
        """
        compare_result = chat.invoke([HumanMessage(content=prompt_compare)])

        # 3. 키워드 추출
        prompt_extract = f"""
다음 문서에서 등장하는 주요 키워드나 성분명, 원재료명 등을 항목별로 나열해주세요. 
주요 성분과 상품명, 원재료명등 상품과 관련된 정보를 반드시 모두 추출하고, 쉼표로 구분해서 출력해주세요:

{parsed_text}
        """
        keyword_response = chat.invoke([HumanMessage(content=prompt_extract)])
        keywords = [k.strip() for k in keyword_response.content.split(",") if k.strip()]

        # 4. CSV 필터링 (combined_text 열 기반으로 검색)
        harmful_match = filter_df_prepared(harmful_df, keywords)
        additive_match = filter_df_prepared(additives_df, keywords)
        customs_match = filter_df_prepared(customs_df, keywords)

        # 5. 각 요약 요청
        def summarize_rows(title, df_match):
            if df_match.empty:
                return f"- {title}: 관련 정보 없음"
            else:
                text = df_match.to_csv(index=False)
                prompt = f"""
아래는 {title}에 관련된 데이터입니다:

{text}

사용자가 해당 성분/이슈에 대해 수출입 및 통관 업무시 알아야 할 주의사항을 요약해 주세요. 수출입입 업무에 대한 내용만 요약하세요.
                """
                return f"- {title}:\n" + chat.invoke([HumanMessage(content=prompt)]).content

        caution_summary = "\n\n".join([
            summarize_rows("유해물질", harmful_match),
            summarize_rows("식품첨가물", additive_match),
            summarize_rows("통관 문제사항", customs_match)
        ])

        # 대화 저장
        messages = [
            {
                "role": "user",
                "content": f"PDF 파일 검증 요청: {file.filename}"
            },
            {
                "role": "assistant",
                "content": {
                    "불일치검사결과": compare_result.content,
                    "성분및통관주의사항": caution_summary
                }
            }
        ]
        
        # conversation_memory.json 파일에 저장
        try:
            file_path = get_conversation_file_path()
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
            else:
                memory = {}
                
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if "pdf_validation" not in memory:
                memory["pdf_validation"] = {}
                
            memory["pdf_validation"][current_time] = messages
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
                
            print(f"대화가 저장되었습니다: {file_path}")
            
        except Exception as e:
            print(f"대화 저장 중 오류 발생: {str(e)}")

        return JSONResponse(content={
            "불일치검사결과": compare_result.content,
            "성분및통관주의사항": caution_summary
        })

    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 