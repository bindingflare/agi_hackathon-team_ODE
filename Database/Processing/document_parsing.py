import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()  

api_key = os.getenv("API_KEY")
print(f"API key: {repr(api_key)}")

# OCR 요청 설정
def parse_pdf(file_path):
    print(f"Parsing: {file_path}")
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {
            "ocr": "force",
            "base64_encoding": "['table']",
            "model": "document-parse"
        }
        headers = {"Authorization": f"Bearer {api_key}"}


        response = requests.post(
            "https://api.upstage.ai/v1/document-digitization",
            headers=headers,
            files=files,
            data=data
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to parse {file_path}: {response.status_code}")
            return None

# 폴더 순회
base_dir = "Database/Local/Forms"

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if filename.startswith("GUIDE") and filename.endswith(".pdf"):
            full_path = os.path.join(root, filename)
            result = parse_pdf(full_path)
            
            if result:
                output_filename = f"PARSED_{filename.replace('.pdf', '.json')}"
                output_path = os.path.join(root, output_filename)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"Saved: {output_path}")
            else:
                print(f"Skipped: {full_path}")

print("Done parsing all GUIDE PDFs.")