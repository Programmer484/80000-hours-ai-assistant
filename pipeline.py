"""Combined pipeline: Extract → Chunk → Upload to Qdrant (additive)"""
from extract_content_cli import extract_all_to_json
from chunk_articles_cli import chunk_from_json_files
from upload_to_qdrant_cli import upload_chunks_additive


def main():
    print("="*80)
    print("80,000 HOURS RAG PIPELINE")
    print("Extract → Chunk → Upload (Additive)")
    print("="*80)
    
    # Step 1: Extract to individual JSON files
    print("\n" + "="*80)
    print("STEP 1: EXTRACTING CONTENT")
    print("="*80)
    extract_all_to_json()
    
    # Step 2: Chunk from JSON files
    print("\n" + "="*80)
    print("STEP 2: CHUNKING ARTICLES")
    print("="*80)
    chunk_from_json_files()
    
    # Step 3: Upload to Qdrant from chunks file (additive)
    print("\n" + "="*80)
    print("STEP 3: UPLOADING TO QDRANT (ADDITIVE)")
    print("="*80)
    upload_chunks_additive()
    
    print("\n" + "="*80)
    print("PIPELINE COMPLETE ✓")
    print("="*80)


if __name__ == "__main__":
    main()
