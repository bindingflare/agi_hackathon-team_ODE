import os
import json
import requests
import fitz  # PyMuPDF
from tempfile import NamedTemporaryFile
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
from requests.exceptions import RequestException, Timeout
import time

def send_chunk_with_retry(chunk_path, api_key, max_retries=3, timeout=300):
    """Send a chunk to the API with retry logic and timeout"""
    for attempt in range(max_retries):
        try:
            with open(chunk_path, "rb") as file:
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
                    data=data,
                    timeout=timeout
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    wait_time = int(response.headers.get('Retry-After', 60))
                    print(f"\nRate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"\nAttempt {attempt + 1} failed: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                        continue
                    response.raise_for_status()
                    
        except Timeout:
            print(f"\nTimeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise
        except RequestException as e:
            print(f"\nRequest error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
        except Exception as e:
            print(f"\nUnexpected error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise

    raise Exception(f"Failed to process chunk after {max_retries} attempts")

def create_pdf_chunks(original_path, max_pages=20):  # Reduced chunk size
    """Split PDF into smaller chunks for processing"""
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"PDF file not found: {original_path}")
        
    doc = fitz.open(original_path)
    total_pages = len(doc)
    chunk_files = []

    try:
        for start in tqdm(range(0, total_pages, max_pages), desc="📄 Creating PDF chunks"):
            end = min(start + max_pages, total_pages)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

            temp_file = NamedTemporaryFile(delete=False, suffix=".pdf")
            new_doc.save(temp_file.name)
            new_doc.close()
            chunk_files.append(temp_file.name)
    finally:
        doc.close()
        
    return chunk_files

def parse_pdf(file_path, api_key):
    """Parse PDF using Upstage API"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
        
    print(f"📄 Starting PDF processing: {file_path}")
    chunk_paths = create_pdf_chunks(file_path)
    merged_result = {"elements": []}
    
    print(f"\nProcessing {len(chunk_paths)} chunks...")

    try:
        progress_bar = tqdm(chunk_paths, desc="🔍 Processing chunks")
        for i, chunk_path in enumerate(progress_bar):
            try:
                progress_bar.set_description(f"🔍 Processing chunk {i+1}/{len(chunk_paths)}")
                result = send_chunk_with_retry(chunk_path, api_key)
                if result and "elements" in result:
                    merged_result["elements"].extend(result["elements"])
                    progress_bar.set_postfix({"elements": len(merged_result["elements"])})
            except Exception as e:
                print(f"Error processing chunk {i+1}: {str(e)}")
                if i == 0:  # If first chunk fails, raise the error
                    raise
                continue  # For other chunks, try to continue
    finally:
        # Clean up chunks
        for chunk_path in tqdm(chunk_paths, desc="🧹 Cleaning up chunks"):
            try:
                os.remove(chunk_path)
            except Exception as e:
                print(f"Warning: Failed to remove chunk file {chunk_path}: {e}")

    print(f"\nSuccessfully processed {len(merged_result['elements'])} elements")
    return merged_result

def extract_text_elements(result, filename):
    """Extract text elements from parsed PDF result"""
    paragraphs = []
    passage_list = []
    clean_filename = os.path.basename(filename)
    idx = 1

    for element in tqdm(result.get("elements", []), desc="📝 Extracting text"):
        try:
            category = element.get("category", "unknown")
            if category in ["paragraph", "list", "table", "heading"]:
                html = element["content"].get("html", "")
                text = BeautifulSoup(html, "html.parser").get_text(strip=True)
                
                # Skip if text is too short or empty
                if not text or len(text) < 10:  # Increased minimum length
                    continue
                    
                paragraphs.append({
                    "id": idx,
                    "page": element["page"],
                    "text": text,
                    "source_file": clean_filename,
                    "category": category
                })
                passage_list.append(text)
                idx += 1
        except KeyError as e:
            print(f"Warning: Missing required field in element: {str(e)}")
            continue
        except Exception as e:
            print(f"Warning: Failed to process element: {str(e)}")
            continue

    if not passage_list:
        raise ValueError("No valid text found in the document")

    return paragraphs, passage_list 