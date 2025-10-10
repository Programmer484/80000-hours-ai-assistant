import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from citation_validator import generate_answer_with_citations, format_citations_display, normalize_text
from config import MODEL_NAME, COLLECTION_NAME

load_dotenv()

LLM_MODEL = "gpt-4o-mini"
SOURCE_COUNT = 10
SCORE_THRESHOLD = 0.4

def retrieve_context(question):
    """Retrieve relevant chunks from Qdrant."""
    start = time.time()
    
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    
    model = SentenceTransformer(MODEL_NAME)
    query_vector = model.encode(question).tolist()
    
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=SOURCE_COUNT,
        score_threshold=SCORE_THRESHOLD,
    )
    print(f"[TIMING] Retrieval: {(time.time() - start)*1000:.2f}ms")
    
    return results.points

def format_context(results):
    """Format retrieved chunks into context string for LLM."""
    context_parts = []
    for i, hit in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}]\n"
            f"Title: {hit.payload['title']}\n"
            f"URL: {hit.payload['url']}\n"
            f"Content: {hit.payload['text']}\n"
        )
    return "\n---\n".join(context_parts)

def ask(question: str, show_context: bool = False) -> Dict[str, Any]:
    """Main RAG function: retrieve context and generate answer with validated citations."""
    total_start = time.time()
    print(f"Question: {question}\n")
    
    # Retrieve relevant chunks
    results = retrieve_context(question)
    
    if not results:
        print("No relevant sources found above the score threshold.")
        return {
            "question": question,
            "answer": "No relevant information found in the knowledge base.",
            "citations": [],
            "sources": []
        }
    
    context = format_context(results)
    print(f"[TIMING] First chunk ready: {(time.time() - total_start)*1000:.2f}ms")
    
    if show_context:
        print("=" * 80)
        print("RETRIEVED CONTEXT:")
        print("=" * 80)
        print(context)
        print("\n")
    
    # Generate answer with citations
    llm_start = time.time()
    result = generate_answer_with_citations(
        question=question,
        context=context,
        results=results,
        llm_model=LLM_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    total_time = (time.time() - total_start) * 1000
    print(f"[TIMING] Total: {total_time:.2f}ms ({total_time/1000:.2f}s)")
    
    # Display answer
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(result["answer"])
    print("\n")
    
    # Display citations
    print("=" * 80)
    print("CITATIONS (Verified Quotes):")
    print("=" * 80)
    print(format_citations_display(result["citations"]))
    
    # Show validation stats
    if result["validation_errors"]:
        print("\n" + "=" * 80)
        print("VALIDATION WARNINGS:")
        print("=" * 80)
        for error in result["validation_errors"]:
            print(f"⚠ [Citation {error['citation_id']}] {error['reason']}")
    
    print("\n" + "=" * 80)
    print(f"Citation Stats: {result['valid_citations']}/{result['total_citations']} citations validated")
    print("=" * 80)
    
    # Save validation results to JSON
    def normalize_dict(obj):
        """Recursively normalize all strings in a dict/list structure."""
        if isinstance(obj, dict):
            return {k: normalize_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize_dict(item) for item in obj]
        elif isinstance(obj, str):
            return normalize_text(obj)
        return obj
    
    validation_output = {
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "validation_errors": result["validation_errors"],
        "stats": {
            "total_citations": result["total_citations"],
            "valid_citations": result["valid_citations"],
            "total_time_ms": total_time
        },
        "sources": [
            {
                "source_id": i,
                "title": hit.payload['title'],
                "url": hit.payload['url'],
                "chunk_id": hit.payload.get('chunk_id'),
                "text": hit.payload['text']
            }
            for i, hit in enumerate(results, 1)
        ]
    }
    
    # Normalize all text in the output
    validation_output = normalize_dict(validation_output)
    
    import json
    with open("validation_results.json", "w", encoding="utf-8") as f:
        json.dump(validation_output, f, ensure_ascii=False, indent=2)
    print("\n[INFO] Validation results saved to validation_results.json")
    
    return {
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "validation_errors": result["validation_errors"],
        "sources": results
    }

def main():
    import sys
    
    # Default test query if no args provided
    if len(sys.argv) < 2:
        question = "Should I plan my entire career?"
        show_context = False
        print(f"[INFO] No query provided, using test query: '{question}'\n")
    else:
        show_context = "--show-context" in sys.argv
        question_parts = [arg for arg in sys.argv[1:] if arg != "--show-context"]
        question = " ".join(question_parts)
    
    ask(question, show_context=show_context)

if __name__ == "__main__":
    main()

