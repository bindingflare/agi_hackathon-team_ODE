import os
import json
import base64
import tempfile
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

# ---- (1) 기존 openai -> Upstage SDK 사용부 ----
# pip install openai
from openai import OpenAI

client = OpenAI(
    api_key="up_LYEjt0aGQV2SPaH22Mos5CqAzbikF",    # 본인의 Upstage API 키
    base_url="https://api.upstage.ai/v1/information-extraction"
)

app = FastAPI()

# ---- (2) 메모리, CSV 로딩 ----
with open("memory.json", "r", encoding="utf-8") as f:
    memory_data = json.load(f)

harmful_df = pd.read_csv("harmful_substances_prepared.csv")  # 유해물질
additives_df = pd.read_csv("food_additives_prepared.csv")     # 식품첨가물
customs_df = pd.read_csv("customs_issues_prepared.csv")       # 통관 문제

def filter_df_prepared(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """combined_text 열에서 keywords 중 1개 이상 포함되면 필터링"""
    mask = df["combined_text"].apply(
        lambda val: any(kw in str(val) for kw in keywords)
    )
    return df[mask]

def get_conversation_file_path():
    """conversation_memory.json 파일의 절대 경로를 반환합니다."""
    # (본인 프로젝트 구조에 맞춰 수정)
    return os.path.join(os.path.dirname(__file__), "conversation_memory.json")

# ---- (3) PDF 체크 API ----
@app.post("/check-pdf")
async def check_pdf(file: UploadFile = File(...)):
    # 1) PDF를 임시 폴더에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # 2) PDF -> base64 인코딩
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        # 3) Upstage information-extraction 호출
        #    실제 스펙이 PDF를 image_url 방식으로 받을 수 있는지 확인 필요
        extraction_response = client.chat.completions.create(
            model="information-extract",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",  # 실제로 PDF 지원 시 "document" 등 다른 키일 수 있음
                            "image_url": {
                                "url": f"data:application/pdf;base64,{base64_pdf}"
                            }
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "document_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "extracted_text": {
                                "type": "string",
                                "description": "문서에서 추출된 전체/주요 텍스트"
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "문서에서 추출된 주요 키워드 목록"
                            },
                            "some_other_field": {
                                "type": "string",
                                "description": "기타 필요한 필드 예시"
                            }
                        },
                        "required": ["extracted_text"]  # 반드시 반환해야 하는 필드
                    }
                }
            }
        )

        # 4) JSON 파싱
        #    extraction_response.choices[0].message.content 가 string 형태의 JSON
        extracted_str = extraction_response.choices[0].message.content
        extracted_json = json.loads(extracted_str)

        # 5) 결과에서 텍스트/키워드 추출
        extracted_text = extracted_json.get("extracted_text", "")
        keywords = extracted_json.get("keywords", [])

        # 6) 메모리 비교(예: '불일치' 검사)
        #    예시: memory_data와 비교 프롬프트 생략 -> 필요하다면
        #          ChatUpstage 호출하여 비교 로직을 짜도 되고,
        #          여기서는 JSON 직접 비교 로직도 가능
        #          간단히 "맞음 or 틀림" 표시 등
        # (데모) 불일치 결과 예시
        compare_result = "메모리 데이터와 비교 결과: 아직 로직 미구현"

        # 7) CSV 검색 (keywords 기반)
        harmful_match = filter_df_prepared(harmful_df, keywords)
        additive_match = filter_df_prepared(additives_df, keywords)
        customs_match = filter_df_prepared(customs_df, keywords)

        def summarize_rows(title, df_match):
            if df_match.empty:
                return f"- {title}: 관련 정보 없음"
            else:
                # 필요한 경우, df_match로부터 간단 요약
                # 여기서는 CSV 값만 바로 표시
                return f"- {title}:\n{df_match.to_csv(index=False)}"

        caution_summary = "\n\n".join([
            summarize_rows("유해물질", harmful_match),
            summarize_rows("식품첨가물", additive_match),
            summarize_rows("통관 문제사항", customs_match)
        ])

        # 8) 대화 내역 구성
        messages = [
            {
                "role": "user",
                "content": f"PDF 파일 검증 요청: {file.filename}"
            },
            {
                "role": "assistant",
                "content": {
                    "불일치검사결과": compare_result,
                    "성분및통관주의사항": caution_summary
                }
            }
        ]

        # 9) 대화 저장 (conversation_memory.json)
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

        # 10) 최종 응답
        return JSONResponse(content={
            "불일치검사결과": compare_result,
            "성분및통관주의사항": caution_summary,
            "extracted_raw": extracted_json  # 디버그용
        })

    finally:
        # 임시 파일 삭제
        os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
