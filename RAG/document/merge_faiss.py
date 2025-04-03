#!/usr/bin/env python3

import os
import pickle
import faiss
from tqdm import tqdm
import json

# Define directory paths
BASE_DIR = "Database"
EMBEDDED_DIR = os.path.join(BASE_DIR, "Embedded")
MERGED_DIR = os.path.join(BASE_DIR, "Merged")

def validate_merge(original_files, merged_index, merged_docstore):
    """Validate that all documents and vectors were properly merged"""
    print("\n=== Validating Merge Results ===")
    
    # Count total vectors and documents from original files
    total_original_vectors = 0
    total_original_docs = 0
    original_docs = []  # Use list instead of set
    
    for index_file in original_files:
        base_name = index_file.replace("faiss_index_", "").replace(".index", "")
        
        # Load original index
        index_path = os.path.join(EMBEDDED_DIR, index_file)
        index = faiss.read_index(index_path)
        total_original_vectors += index.ntotal
        
        # Load original docstore
        store_path = os.path.join(EMBEDDED_DIR, f"faiss_store_{base_name}.pkl")
        with open(store_path, "rb") as f:
            docstore = pickle.load(f)
            index_to_docstore_id = pickle.load(f)
            # Count documents by checking index_to_docstore_id length
            total_original_docs += len(index_to_docstore_id)
            # Get all documents from docstore
            for doc_id in index_to_docstore_id.values():
                doc = docstore.search(doc_id)
                if doc is not None:
                    original_docs.append(doc)  # Use append instead of add
    
    # Compare with merged results
    print(f"Original total vectors: {total_original_vectors}")
    print(f"Merged total vectors: {merged_index.ntotal}")
    print(f"Original total documents: {total_original_docs}")
    print(f"Merged total documents: {len(merged_docstore)}")
    
    if total_original_vectors != merged_index.ntotal:
        raise ValueError(f"Vector count mismatch! Original: {total_original_vectors}, Merged: {merged_index.ntotal}")
    
    if total_original_docs != len(merged_docstore):
        raise ValueError(f"Document count mismatch! Original: {total_original_docs}, Merged: {len(merged_docstore)}")
    
    print("✅ Merge validation successful!")

def merge_faiss_indices():
    """Merge all FAISS indices into one combined index with sequential IDs"""
    print("\n=== Starting FAISS Index Merging ===\n")
    
    # Create Merged directory if it doesn't exist
    os.makedirs(MERGED_DIR, exist_ok=True)
    
    # Get all index files
    index_files = [f for f in os.listdir(EMBEDDED_DIR) if f.startswith("faiss_index_") and f.endswith(".index")]
    if not index_files:
        raise ValueError("No FAISS index files found to merge")
    
    print(f"Found {len(index_files)} index files to merge")
    
    # Initialize merged store
    merged_index = None
    merged_docstore = {}
    merged_index_to_docstore_id = {}
    current_id = 1  # Start from 1 for both document and index IDs
    doc_counter = 1  # Start document IDs from 1
    
    # Process each index file
    for index_file in tqdm(index_files, desc="Merging indices"):
        base_name = index_file.replace("faiss_index_", "").replace(".index", "")
        
        # Load index
        index_path = os.path.join(EMBEDDED_DIR, index_file)
        index = faiss.read_index(index_path)
        
        # Load docstore
        store_path = os.path.join(EMBEDDED_DIR, f"faiss_store_{base_name}.pkl")
        with open(store_path, "rb") as f:
            docstore = pickle.load(f)
            index_to_docstore_id = pickle.load(f)
        
        # Merge docstore and mappings with new sequential IDs
        if merged_index is None:
            merged_index = index
            # For the first index, just copy the mappings
            for old_id, doc_id in index_to_docstore_id.items():
                new_id = old_id
                new_doc_id = str(doc_counter)  # Use sequential number as new doc ID
                merged_index_to_docstore_id[new_id] = new_doc_id
                # Get document from docstore using the proper method
                doc = docstore.search(doc_id)
                if doc is not None:
                    # Store the document with all its metadata
                    merged_docstore[new_doc_id] = {
                        "id": doc_counter,
                        "page": doc.metadata.get("page", 1),
                        "text": doc.page_content,
                        "source_file": doc.metadata.get("source_file", ""),
                        "category": doc.metadata.get("category", "unknown")
                    }
                doc_counter += 1
        else:
            # Get the number of vectors in the merged index before merging
            prev_ntotal = merged_index.ntotal
            # Add vectors from the new index to the merged index
            merged_index.add(index.reconstruct_n(0, index.ntotal))
            # Update the index_to_docstore_id mapping with shifted IDs
            for old_id, doc_id in index_to_docstore_id.items():
                new_id = prev_ntotal + old_id
                new_doc_id = str(doc_counter)  # Use sequential number as new doc ID
                merged_index_to_docstore_id[new_id] = new_doc_id
                # Get document from docstore using the proper method
                doc = docstore.search(doc_id)
                if doc is not None:
                    # Store the document with all its metadata
                    merged_docstore[new_doc_id] = {
                        "id": doc_counter,
                        "page": doc.metadata.get("page", 1),
                        "text": doc.page_content,
                        "source_file": doc.metadata.get("source_file", ""),
                        "category": doc.metadata.get("category", "unknown")
                    }
                doc_counter += 1
    
    # Validate the merge
    validate_merge(index_files, merged_index, merged_docstore)
    
    # Save merged files
    print("\nSaving merged files...")
    
    # Save merged index
    merged_index_path = os.path.join(MERGED_DIR, "merged_faiss.index")
    faiss.write_index(merged_index, merged_index_path)
    print(f"✅ Merged index saved: {merged_index_path}")
    
    # Save merged docstore and mappings
    merged_store_path = os.path.join(MERGED_DIR, "merged_faiss.pkl")
    with open(merged_store_path, "wb") as f:
        pickle.dump(merged_docstore, f)
        pickle.dump(merged_index_to_docstore_id, f)
    print(f"✅ Merged docstore saved: {merged_store_path}")
    
    # Save metadata summary with full document information
    metadata = {
        "total_documents": len(merged_docstore),
        "total_vectors": merged_index.ntotal,
        "source_files": index_files,
        "documents": list(merged_docstore.values()),  # Include all document data
        "original_document_count": len(merged_docstore),
        "original_vector_count": merged_index.ntotal
    }
    metadata_path = os.path.join(MERGED_DIR, "merge_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ Metadata summary saved: {metadata_path}")
    
    # Save just the documents array as a separate JSON file
    documents_path = os.path.join(MERGED_DIR, "merged_documents.json")
    with open(documents_path, "w", encoding="utf-8") as f:
        json.dump(list(merged_docstore.values()), f, ensure_ascii=False, indent=2)
    print(f"✅ Documents JSON saved: {documents_path}")
    
    # Print summary
    print("\n=== Merging Complete ===")
    print(f"Total documents: {len(merged_docstore)}")
    print(f"Total vectors: {merged_index.ntotal}")
    print(f"Merged files saved in: {MERGED_DIR}")

if __name__ == "__main__":
    try:
        merge_faiss_indices()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        exit(1) 