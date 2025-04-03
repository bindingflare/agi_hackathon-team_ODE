import os
import json
import re
import pickle
import faiss
import numpy as np
from typing import List
from fastapi import FastAPI, BackgroundTasks
from dotenv import load_dotenv
from datetime import datetime
from langchain_upstage import UpstageEmbeddings
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY not found in environment variables")

# Define directory paths
BASE_DIR = "Database"
WEB_DIR = os.path.join(BASE_DIR, "Web")
MERGED_DIR = os.path.join(BASE_DIR, "merged")

# Define consistent file names
MERGED_INDEX_FILE = "merged_faiss.index"
MERGED_STORE_FILE = "merged_faiss.pkl"
MERGED_METADATA_FILE = "merged_documents.json"

app = FastAPI()

def get_max_id_from_metadata(metadata_path):
    """Get the maximum ID from existing metadata file"""
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
            if metadata_list:
                return max(item.get('id', 0) for item in metadata_list)
    return 0

def process_search_result(search_result):
    """Process a single search result and create embeddings"""
    print("\nProcessing search result...")
    
    # Get max ID from existing merged metadata
    merged_metadata_path = os.path.join(MERGED_DIR, MERGED_METADATA_FILE)
    next_id = get_max_id_from_metadata(merged_metadata_path) + 1
    print(f"Next ID for new document: {next_id}")
    
    # Extract content and metadata
    content = search_result["result"]
    metadata = {
        "id": next_id,
        "page": 1,
        "text": content,
        "source_file": f"{search_result['timestamp']}.json",
        "category": "paragraph"
    }
    
    print("\nCreated metadata:")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    # Create document
    document = Document(
        page_content=content,
        metadata=metadata
    )
    
    # Initialize embeddings
    embeddings = UpstageEmbeddings(api_key=api_key, model="embedding-passage")
    
    # Process embeddings
    try:
        doc_embeddings = embeddings.embed_documents([document.page_content])
    except Exception as e:
        print(f"\n⚠️ Error in embedding: {str(e)}")
        print("Falling back to individual processing...")
        try:
            doc_embeddings = [embeddings.embed_query(document.page_content)]
        except Exception as e:
            print(f"Failed to embed text: {str(e)}")
            doc_embeddings = [[0.0] * 768]
    
    # Create merged directory if it doesn't exist
    os.makedirs(MERGED_DIR, exist_ok=True)
    
    # Define paths for merged data
    merged_index_path = os.path.join(MERGED_DIR, MERGED_INDEX_FILE)
    merged_store_path = os.path.join(MERGED_DIR, MERGED_STORE_FILE)
    merged_metadata_path = os.path.join(MERGED_DIR, MERGED_METADATA_FILE)
    
    # Create a FAISS index from the document
    faiss_store = FAISS.from_documents([document], embeddings)
    
    # Load existing merged data if it exists
    if os.path.exists(merged_index_path) and os.path.exists(merged_store_path) and os.path.exists(merged_metadata_path):
        print("\nLoading existing merged data...")
        existing_index = faiss.read_index(merged_index_path)
        with open(merged_store_path, "rb") as f:
            existing_docstore = pickle.load(f)
            existing_index_to_docstore_id = pickle.load(f)
        
        # Get current size before adding new index
        current_size = existing_index.ntotal
        
        # Add new index at the end
        new_index = faiss_store.index
        xq = np.zeros((1, existing_index.d), dtype='float32')
        new_index.reconstruct(0, xq[0])
        existing_index.add(xq)
        
        # Update docstore and mappings
        new_doc = faiss_store.docstore.search(str(next_id))
        existing_docstore[str(next_id)] = new_doc
        existing_index_to_docstore_id[current_size] = str(next_id)
        
        # Load and update metadata
        with open(merged_metadata_path, "r", encoding='utf-8') as f:
            merged_metadata = json.load(f)
        merged_metadata.append(metadata)
        
        # Save merged results
        print("\nSaving merged results...")
        faiss.write_index(existing_index, merged_index_path)
        with open(merged_store_path, "wb") as f:
            pickle.dump(existing_docstore, f)
            pickle.dump(existing_index_to_docstore_id, f)
        with open(merged_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(merged_metadata, f, ensure_ascii=False, indent=2)
        
        print(f"\nMerge complete! Total vectors in merged index: {existing_index.ntotal}")
        print(f"Total metadata entries: {len(merged_metadata)}")
    else:
        print("\nNo existing merged data found, creating new...")
        faiss.write_index(faiss_store.index, merged_index_path)
        with open(merged_store_path, "wb") as f:
            pickle.dump(faiss_store.docstore, f)
            pickle.dump(faiss_store.index_to_docstore_id, f)
        with open(merged_metadata_path, 'w', encoding='utf-8') as f:
            json.dump([metadata], f, ensure_ascii=False, indent=2)
        
        print(f"\nNew store created! Total vectors: {faiss_store.index.ntotal}")

@app.post("/process")
async def process_endpoint(background_tasks: BackgroundTasks, search_result: dict):
    """Process a search result and add it to the merged index"""
    background_tasks.add_task(process_search_result, search_result)
    return {"message": "Processing started", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010) 