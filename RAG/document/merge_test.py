#!/usr/bin/env python3

import os
import pickle
import faiss
import glob
from tqdm import tqdm

# Define directory paths
BASE_DIR = "Database"
WEB_DIR = os.path.join(BASE_DIR, "Web")
MERGED_DIR = os.path.join(BASE_DIR, "Merged")
MERGED_TEST_DIR = os.path.join(BASE_DIR, "merged_test")

def merge_indices():
    """Merge FAISS indices from Web with existing merged index"""
    print("\nStarting merge process...")
    
    # Create merged_test directory if it doesn't exist
    os.makedirs(MERGED_TEST_DIR, exist_ok=True)
    
    # Load existing merged index and docstore
    merged_index_path = os.path.join(MERGED_DIR, "merged_faiss_index.index")
    merged_store_path = os.path.join(MERGED_DIR, "merged_faiss_store.pkl")
    
    if os.path.exists(merged_index_path) and os.path.exists(merged_store_path):
        print("Loading existing merged index and docstore...")
        merged_index = faiss.read_index(merged_index_path)
        with open(merged_store_path, "rb") as f:
            merged_docstore = pickle.load(f)
            merged_index_to_docstore_id = pickle.load(f)
    else:
        raise ValueError("Existing merged files not found!")
    
    # Get all Web indices
    web_indices = glob.glob(os.path.join(WEB_DIR, "faiss_index*.index"))
    print(f"\nFound {len(web_indices)} indices in Web directory")
    
    # Process each Web index
    for web_index_path in tqdm(web_indices, desc="Merging indices"):
        base_filename = os.path.basename(web_index_path).replace("faiss_index", "").replace(".index", "")
        web_store_path = os.path.join(WEB_DIR, f"faiss_store{base_filename}.pkl")
        
        # Load Web index and docstore
        web_index = faiss.read_index(web_index_path)
        with open(web_store_path, "rb") as f:
            web_docstore = pickle.load(f)
            web_index_to_docstore_id = pickle.load(f)
        
        # Get the current size of merged index
        current_size = merged_index.ntotal
        
        # Merge the indices
        faiss.merge_into(merged_index, web_index, shift_ids=True)
        
        # Update docstore and mappings
        for old_id, doc_id in web_index_to_docstore_id.items():
            new_id = old_id + current_size
            merged_index_to_docstore_id[new_id] = doc_id
            merged_docstore[doc_id] = web_docstore[doc_id]
    
    # Save merged results to merged_test directory
    print("\nSaving merged results...")
    new_merged_index_path = os.path.join(MERGED_TEST_DIR, "merged_faiss_index.index")
    new_merged_store_path = os.path.join(MERGED_TEST_DIR, "merged_faiss_store.pkl")
    
    # Save merged index
    faiss.write_index(merged_index, new_merged_index_path)
    print(f"✅ Merged index saved: {new_merged_index_path}")
    
    # Save merged docstore
    with open(new_merged_store_path, "wb") as f:
        pickle.dump(merged_docstore, f)
        pickle.dump(merged_index_to_docstore_id, f)
    print(f"✅ Merged docstore saved: {new_merged_store_path}")
    
    print(f"\nMerge complete! Total vectors in merged index: {merged_index.ntotal}")

if __name__ == "__main__":
    merge_indices() 