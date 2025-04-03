from dotenv import load_dotenv
import os
import json
from bs4 import BeautifulSoup
from openai import OpenAI
from tqdm import tqdm
import re

# 환경 변수 로드
load_dotenv()
api_key = os.getenv("API_KEY")

# Upstage OpenAI Client
client = OpenAI(
    api_key=api_key,
    base_url="https://api.upstage.ai/v1"
)

# Forms 디렉토리 기준 경로
base_dir = "Database/Local/Forms"

def embed_with_retries(batch_texts, max_retries=3):
    # Try decreasing batch size in chunks
    current_batch_size = len(batch_texts)

    while current_batch_size >= 2:
        chunks = [
            batch_texts[i:i + current_batch_size]
            for i in range(0, len(batch_texts), current_batch_size)
        ]

        all_embeddings = []
        success = True

        for chunk in chunks:
            try:
                response = client.embeddings.create(
                    model="embedding-passage",
                    input=chunk
                ).data
                all_embeddings.extend([item.embedding for item in response])
            except Exception as e:
                print(f"⚠️ Failed at chunk size {current_batch_size}. Retrying smaller chunks... ({e})")
                success = False
                break  # Try smaller chunks

        if success:
            return all_embeddings

        current_batch_size = current_batch_size // 2

    print("❌ Failed to embed this batch after retries.")
    return None

# 모든 하위 폴더 순회
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.startswith("PARSED_GUIDE") and file.endswith(".json"):
            parsed_path = os.path.join(root, file)
            print(f"\n🔍 Processing: {parsed_path}")

            with open(parsed_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # paragraph 추출
            paragraphs = []
            passage_list = []
            folder_name = os.path.basename(root)
            keyword = re.sub(r"^\d+_", "", folder_name)
            clean_filename = file.replace("PARSED_", "")

            idx = 1
            for element in data.get("elements", []):
                if element.get("category") in ["paragraph","list","table"]:
                    html = element["content"].get("html", "")
                    text = BeautifulSoup(html, "html.parser").get_text(strip=True)
                    if text and len(text) >= 10:
                        paragraphs.append({
                            "id": idx,
                            "page": element["page"],
                            "text": text,
                            "keyword": keyword,
                            "source_file": clean_filename
                        })
                        passage_list.append(text)
                        idx += 1

            if not passage_list:
                print("⚠️ No valid paragraph text found. Skipping.")
                continue

            # 배치 임베딩 (adaptive batch size)
            all_embeddings = []
            batch_size = 100
            for i in tqdm(range(0, len(passage_list), batch_size), desc="Embedding"):
                batch = passage_list[i:i + batch_size]
                batch_embeddings = embed_with_retries(batch)
                if batch_embeddings:
                    all_embeddings.extend(batch_embeddings)

            if len(all_embeddings) != len(paragraphs):
                print("Embedding count mismatch. Skipping file.")
                continue

            for i in range(len(paragraphs)):
                paragraphs[i]["embedding"] = all_embeddings[i]

            # 저장
            embedded_filename = file.replace("PARSED_", "EMBEDDED_PARSED_")
            embedded_path = os.path.join(root, embedded_filename)
            with open(embedded_path, "w", encoding="utf-8") as f:
                json.dump(paragraphs, f, ensure_ascii=False, indent=2)
            print(f"Saved: {embedded_path}")

print("\n🏁 All forms processed.")