#!/usr/bin/env python3

import os
import json
import pickle
import faiss
import glob
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
import numpy as np

# LangChain imports
from langchain_upstage import UpstageEmbeddings
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

# Define directory paths
BASE_DIR = "Database"
WEB_DIR = os.path.join(BASE_DIR, "Web")
MERGED_DIR = os.path.join(BASE_DIR, "merged")

# Define consistent file names
MERGED_INDEX_FILE = "merged_faiss.index"
MERGED_STORE_FILE = "merged_faiss.pkl"
MERGED_METADATA_FILE = "merged_documents.json"

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
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY not found in environment variables")
    
    # Get max ID from existing merged metadata
    merged_metadata_path = os.path.join(MERGED_DIR, MERGED_METADATA_FILE)
    next_id = get_max_id_from_metadata(merged_metadata_path) + 1
    print(f"Next ID for new document: {next_id}")
    
    # Extract content and metadata
    content = search_result["result"]
    metadata = {
        "id": next_id,  # Use incremented ID
        "page": 1,  # Since it's a search result, use page 1
        "text": content,  # The actual search result text
        "source_file": f"{search_result['timestamp']}.json",  # Use timestamp without prefix
        "category": "paragraph"  # Since it's a search result text, use paragraph
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
    
    # Process embeddings in batches
    batch_size = 70  # Adjust based on API limits and performance
    doc_embeddings = []
    
    try:
        # Use embed_documents for batch processing
        batch_embeddings = embeddings.embed_documents([document.page_content])
        doc_embeddings.extend(batch_embeddings)
    except Exception as e:
        print(f"\n⚠️ Error in batch processing: {str(e)}")
        # Fallback to individual processing if batch fails
        print("Falling back to individual processing...")
        try:
            embedding = embeddings.embed_query(document.page_content)
            doc_embeddings.append(embedding)
        except Exception as e:
            print(f"Failed to embed text: {str(e)}")
            # Add a zero vector as placeholder
            doc_embeddings.append([0.0] * 768)  # Assuming 768-dimensional embeddings
    
    # Create merged directory if it doesn't exist
    os.makedirs(MERGED_DIR, exist_ok=True)
    
    # Define paths for merged data
    merged_index_path = os.path.join(MERGED_DIR, MERGED_INDEX_FILE)
    merged_store_path = os.path.join(MERGED_DIR, MERGED_STORE_FILE)
    merged_metadata_path = os.path.join(MERGED_DIR, MERGED_METADATA_FILE)
    
    # Create a FAISS index from the document using the Upstage embeddings
    # Create a new FAISS store using from_documents like in main.py
    faiss_store = FAISS.from_documents([document], embeddings)
    
    # Load existing merged data if it exists
    if os.path.exists(merged_index_path) and os.path.exists(merged_store_path) and os.path.exists(merged_metadata_path):
        print("\nLoading existing merged data...")
        # Load the existing FAISS store
        existing_index = faiss.read_index(merged_index_path)
        with open(merged_store_path, "rb") as f:
            existing_docstore = pickle.load(f)
            existing_index_to_docstore_id = pickle.load(f)
        
        # Get current size before adding new index
        current_size = existing_index.ntotal
        
        # Add new index at the end
        new_index = faiss_store.index
        # Get the vectors from the new index
        xq = np.zeros((1, existing_index.d), dtype='float32')
        new_index.reconstruct(0, xq[0])
        existing_index.add(xq)
        
        # Update docstore and mappings
        # Get the document from the new store and add it to existing docstore
        new_doc = faiss_store.docstore.search(str(next_id))
        existing_docstore[str(next_id)] = new_doc
        existing_index_to_docstore_id[current_size] = str(next_id)
        
        # Load and update metadata
        with open(merged_metadata_path, "r", encoding='utf-8') as f:
            merged_metadata = json.load(f)
        merged_metadata.append(metadata)
        
        # Save merged results
        print("\nSaving merged results...")
        
        # Save merged index
        faiss.write_index(existing_index, merged_index_path)
        print(f"✅ Merged index saved: {merged_index_path}")
        
        # Save merged docstore
        with open(merged_store_path, "wb") as f:
            pickle.dump(existing_docstore, f)
            pickle.dump(existing_index_to_docstore_id, f)
        print(f"✅ Merged docstore saved: {merged_store_path}")
        
        # Save merged metadata
        with open(merged_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(merged_metadata, f, ensure_ascii=False, indent=2)
        print(f"✅ Merged metadata saved: {merged_metadata_path}")
        
        print(f"\nMerge complete! Total vectors in merged index: {existing_index.ntotal}")
        print(f"Total metadata entries: {len(merged_metadata)}")
    else:
        print("\nNo existing merged data found, creating new...")
        # Save the new store directly
        print("\nSaving new store...")
        
        # Save index
        faiss.write_index(faiss_store.index, merged_index_path)
        print(f"✅ Index saved: {merged_index_path}")
        
        # Save docstore
        with open(merged_store_path, "wb") as f:
            pickle.dump(faiss_store.docstore, f)
            pickle.dump(faiss_store.index_to_docstore_id, f)
        print(f"✅ Docstore saved: {merged_store_path}")
        
        # Save metadata
        with open(merged_metadata_path, 'w', encoding='utf-8') as f:
            json.dump([metadata], f, ensure_ascii=False, indent=2)
        print(f"✅ Metadata saved: {merged_metadata_path}")
        
        print(f"\nNew store created! Total vectors: {faiss_store.index.ntotal}")

if __name__ == "__main__":
    # Test data
    search_result = {
        "query": "웹 검색을 통해 CBP form 28을 작성할 때 어떤 것을 숙지해야 하는지 설명해줘",
        "result": "CBP 양식 28(CBP Form 28)은 미국 세관 및 국경보호국(U.S. Customs and Border Protection, CBP)이 수입자에게 추가 정보를 요청할 때 사용하는 공식 문서입니다...",
        "timestamp": "20250404_011703"
    }
    
    # Process the search result and merge directly
    process_search_result(search_result)