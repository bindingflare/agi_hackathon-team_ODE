import os
import json
import pickle
import faiss
import argparse
from dotenv import load_dotenv
from tqdm import tqdm

# LangChain imports
from langchain_upstage import UpstageEmbeddings
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

# Import utility functions
from utils import parse_pdf, extract_text_elements

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY not found in environment variables")

# Define directory paths
BASE_DIR = "Database"
GUIDE_DIR = os.path.join(BASE_DIR, "Guide")
PARSED_DIR = os.path.join(BASE_DIR, "Parsed")
EMBEDDED_DIR = os.path.join(BASE_DIR, "Embedded")

def process_pdf(filename):
    print("\n=== Starting PDF Processing ===\n")
    
    # Construct full path to PDF in Guide directory
    pdf_path = os.path.join(GUIDE_DIR, filename)
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found in Guide directory: {filename}")

    # Parse PDF
    result = parse_pdf(pdf_path, api_key)
    if not result or not result.get("elements"):
        raise ValueError("Failed to parse PDF or no elements found")

    # Save parsed JSON
    parsed_filename = f"PARSED_{filename.replace('.pdf', '.json')}"
    parsed_path = os.path.join(PARSED_DIR, parsed_filename)
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    print(f"✅ Parsed JSON saved: {parsed_path}")

    print("\n=== Starting Text Extraction ===\n")
    
    # Extract elements using utility function
    paragraphs, passage_list = extract_text_elements(result, pdf_path)
    print(f"\nFound {len(passage_list)} text segments to embed")
    
    print("\n=== Starting Embedding Process using UpstageEmbeddings ===\n")
    
    # Initialize embeddings
    embeddings = UpstageEmbeddings(api_key=api_key, model="embedding-passage")
    
    # Process embeddings in batches
    batch_size = 70  # Adjust based on API limits and performance
    doc_embeddings = []
    
    for i in tqdm(range(0, len(passage_list), batch_size), desc="🔗 Creating embeddings"):
        batch = passage_list[i:i + batch_size]
        try:
            # Use embed_documents for batch processing
            batch_embeddings = embeddings.embed_documents(batch)
            doc_embeddings.extend(batch_embeddings)
        except Exception as e:
            print(f"\n⚠️ Error in batch {i//batch_size + 1}: {str(e)}")
            # Fallback to individual processing if batch fails
            print("Falling back to individual processing...")
            for text in batch:
                try:
                    embedding = embeddings.embed_query(text)
                    doc_embeddings.append(embedding)
                except Exception as e:
                    print(f"Failed to embed text: {str(e)}")
                    # Add a zero vector as placeholder
                    doc_embeddings.append([0.0] * 768)  # Assuming 768-dimensional embeddings
    
    if len(doc_embeddings) != len(paragraphs):
        raise ValueError("Embedding count mismatch")
    
    # Create Document objects for FAISS indexing
    documents = [
        Document(
            page_content=p["text"],
            metadata={
                "id": p["id"],
                "page": p["page"],
                "source_file": p["source_file"],
                "category": p.get("category", "unknown")
            }
        )
        for p in paragraphs
    ]
    
    # Create a FAISS index from the documents using the Upstage embeddings
    faiss_store = FAISS.from_documents(documents, embeddings)
    
    # Save the FAISS index and docstore
    base_filename = filename.replace('.pdf', '')
    
    # Save FAISS index (vectors)
    faiss_index_path = os.path.join(EMBEDDED_DIR, f"faiss_index_{base_filename}.index")
    faiss.write_index(faiss_store.index, faiss_index_path)
    print(f"✅ FAISS index saved: {faiss_index_path}")
    
    # Save docstore and mappings
    faiss_pkl_path = os.path.join(EMBEDDED_DIR, f"faiss_store_{base_filename}.pkl")
    with open(faiss_pkl_path, "wb") as f:
        pickle.dump(faiss_store.docstore, f)
        pickle.dump(faiss_store.index_to_docstore_id, f)
    print(f"✅ FAISS docstore saved: {faiss_pkl_path}")
    
    # Save metadata for reference
    metadata_path = os.path.join(EMBEDDED_DIR, f"metadata_{base_filename}.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(paragraphs, f, ensure_ascii=False, indent=2)
    print(f"✅ Metadata saved: {metadata_path}")
    
    print("\n🏁 Processing completed successfully!")

def load_faiss_store(base_filename):
    """Load a previously saved FAISS store"""
    faiss_index_path = os.path.join(EMBEDDED_DIR, f"faiss_index_{base_filename}.index")
    faiss_pkl_path = os.path.join(EMBEDDED_DIR, f"faiss_store_{base_filename}.pkl")
    
    if not os.path.exists(faiss_index_path) or not os.path.exists(faiss_pkl_path):
        raise FileNotFoundError("FAISS index or docstore files not found")
    
    # Load the FAISS index
    index = faiss.read_index(faiss_index_path)
    
    # Load the docstore and mappings
    with open(faiss_pkl_path, "rb") as f:
        docstore = pickle.load(f)
        index_to_docstore_id = pickle.load(f)
    
    # Create embeddings instance
    embeddings = UpstageEmbeddings(api_key=api_key, model="embedding-passage")
    
    # Reconstruct the FAISS store
    faiss_store = FAISS(embeddings.embed_query, index, docstore, index_to_docstore_id)
    
    return faiss_store

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a single PDF file from the Guide directory")
    parser.add_argument("filename", help="Name of the PDF file in the Guide directory (e.g., 'document.pdf')")
    args = parser.parse_args()

    try:
        process_pdf(args.filename)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        exit(1)