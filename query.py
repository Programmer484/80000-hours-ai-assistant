import os
import json
import time
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from citations import parse_llm_response, process_citations, format_citations_display
from config import MODEL_NAME, COLLECTION_NAME

load_dotenv()

LLM_MODEL = "gpt-4o"
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
    
    elapsed = (time.time() - start) * 1000
    print(f"[TIMING] Retrieval: {elapsed:.0f}ms")
    
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

def generate_answer_with_citations(
        question: str, 
        context: str, 
        results: List[Any],
        llm_model: str,
        openai_api_key: str
    ) -> Dict[str, Any]:
    """Generate answer with structured citations using OpenAI.
    
    Args:
        question: User's question
        context: Formatted context from source chunks
        results: Source chunks from Qdrant
        llm_model: OpenAI model name
        openai_api_key: OpenAI API key
        
    Returns:
        Dict with answer and validated citations
    """
    client = OpenAI(api_key=openai_api_key)
    
    system_prompt = """Answer the user's question using ONLY the provided sources from 80,000 Hours articles.

        STEP 1: Write your answer
        - Write a clear, concise answer to the question
        - Use a natural, conversational tone
        - After EACH substantive claim, add [1], [2], [3], etc. in order
        - Example: "Career capital is important [1]. You can build it through work [2]."

        STEP 2: Provide citations
        - For each [N] in your answer, provide a citation with:
        * citation_id: The number from your answer (1 for [1], 2 for [2], etc.)
        * source_id: Which source it came from (match the [Source N] label exactly)
        * quote: Copy the EXACT sentences from that source, word-for-word

        EXAMPLE - If you found text in [Source 3]:
        - Your answer: "Career capital helps you succeed [1]."
        - Your citation: {"citation_id": 1, "source_id": 3, "quote": "Career capital includes..."}
        
        CRITICAL RULES:
        1. Number citations in ORDER: [1] is first, [2] is second, [3] is third, etc.
        2. Copy quotes EXACTLY - no changes, no ellipses, no paraphrasing
        3. source_id MUST match the source number: [Source 1] → source_id: 1, [Source 5] → source_id: 5
        4. Each quote must be complete sentences from the source

        OUTPUT FORMAT (valid JSON):
        {
        "answer": "Your answer with [1], [2], [3] after each claim.",
        "citations": [
            {
            "citation_id": 1,
            "source_id": 2,
            "quote": "Exact sentence from the source."
            },
            {
            "citation_id": 2,
            "source_id": 5,
            "quote": "Another exact sentence from a different source."
            }
        ]
        }"""

    user_prompt = f"""Context from 80,000 Hours articles:

        {context}

        Question: {question}

        Provide your answer in JSON format with exact quotes from the sources."""

    llm_start = time.time()
    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    llm_time = (time.time() - llm_start) * 1000
    print(f"[TIMING] LLM call: {llm_time:.0f}ms")
    
    # Parse LLM response
    parsed = parse_llm_response(response.choices[0].message.content)
    if "validation_errors" in parsed:
        return {
            "answer": parsed["answer"], # raw llm response
            "citations": [],
            "validation_errors": parsed["validation_errors"],
            "total_citations": 0,
            "valid_citations": 0
        }
    
    answer = parsed.get("answer", "")
    citations = parsed.get("citations", [])
    
    # Validate citations
    validation_start = time.time()
    result = process_citations(citations, results)
    validation_time = (time.time() - validation_start) * 1000
    print(f"[TIMING] Validation: {validation_time:.0f}ms")
    
    return {
        "answer": answer,
        "citations": result["validated_citations"],
        "validation_errors": result["validation_errors"],
        "total_citations": len(citations),
        "valid_citations": len(result["validated_citations"])
    }

def save_validation_results(question: str, result: Dict[str, Any], results: List[Any], _unused_time: float):
    """Save detailed validation results to JSON file for debugging."""
    validation_output = {
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "validation_errors": result["validation_errors"],
        "stats": {
            "total_citations": result["total_citations"],
            "valid_citations": result["valid_citations"]
        },
        "sources": [
            {
                "source_id": i,
                "title": hit.payload['title'],
                "url": hit.payload['url'],
                "chunk_id": hit.payload.get('chunk_id'),
                "cosine_similarity": hit.score,  # Vector similarity from Qdrant
                "text": hit.payload['text']
            }
            for i, hit in enumerate(results, 1)
        ]
    }
    
    with open("validation_results.json", "w", encoding="utf-8") as f:
        json.dump(validation_output, f, ensure_ascii=False, indent=2)
    print("\n[INFO] Validation results saved to validation_results.json")

def display_results(question: str, result: Dict[str, Any], context: str = None):
    """Display query results to console."""
    print(f"Question: {question}\n")
    
    if context:
        print("=" * 80)
        print("RETRIEVED CONTEXT:")
        print("=" * 80)
        print(context)
        print("\n")
    
    print("=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(result["answer"])
    print("\n")
    
    print("=" * 80)
    print("CITATIONS (Verified Quotes):")
    print("=" * 80)
    print(format_citations_display(result["citations"]))
    
    if result["validation_errors"]:
        print("\n" + "=" * 80)
        print("VALIDATION WARNINGS:")
        print("=" * 80)
        for error in result["validation_errors"]:
            print(f"⚠ [Citation {error['citation_id']}] {error['reason']}")
    
    print("\n" + "=" * 80)
    print(f"Citation Stats: {result['valid_citations']}/{result['total_citations']} citations validated")
    print("=" * 80)

def ask(question: str, show_context: bool = False) -> Dict[str, Any]:
    """Main RAG function: retrieve context and generate answer with validated citations."""
    total_start = time.time()
    
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
    
    result = generate_answer_with_citations(
        question=question,
        context=context,
        results=results,
        llm_model=LLM_MODEL,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    total_time = (time.time() - total_start) * 1000
    print(f"[TIMING] Total: {total_time:.0f}ms")
    
    # Display results
    display_results(question, result, context if show_context else None)
    
    # Save debug output
    save_validation_results(question, result, results, 0)
    
    return {
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "validation_errors": result["validation_errors"],
        "sources": results
    }
