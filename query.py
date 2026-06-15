"""Query module for RAG system with background model loading."""

import os
import re
import json
import time
import threading
from typing import Dict, Any, List

from dotenv import load_dotenv
from openai import OpenAI
import anthropic
from qdrant_client import QdrantClient

from citations import parse_llm_response, process_citations, format_citations_display
from config import MODEL_NAME, COLLECTION_NAME

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

LLM_MODEL = "claude-sonnet-4-6"
SOURCE_COUNT = 10
SCORE_THRESHOLD = 0.4

# JSON schema for structured synthesis output (enforced via output_config.format).
# Guarantees a parseable shape so citation validation never sees malformed JSON.
CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation_id": {"type": "integer"},
                    "source_id": {"type": "integer"},
                    "quote": {"type": "string"},
                },
                "required": ["citation_id", "source_id", "quote"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answer", "citations"],
    "additionalProperties": False,
}

# ============================================================================
# Context Retrieval
# ============================================================================

# ============================================================================
# Context Retrieval
# ============================================================================

def retrieve_context(question):
    """Retrieve relevant chunks from Qdrant."""
    start = time.time()
    
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = openai_client.embeddings.create(
        input=question,
        model=MODEL_NAME
    )
    query_vector = response.data[0].embedding
    
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

# ============================================================================
# LLM Answer Generation
# ============================================================================

def reconcile_citation_markers(answer: str, validated_citations: List[Dict[str, Any]]):
    """Reconcile in-text [N] markers with the citations that survived validation.

    A marker whose citation was dropped during validation (quote didn't match a
    source) would otherwise render as raw "[5]" text with no link. This removes
    those orphaned markers and renumbers the survivors sequentially, so every
    visible [N] maps to a real, clickable citation and the numbering has no gaps.

    Returns (cleaned_answer, renumbered_citations).
    """
    by_id = {c["citation_id"]: c for c in validated_citations}
    new_citations: List[Dict[str, Any]] = []

    def repl(match: "re.Match") -> str:
        old_id = int(match.group(1))
        cit = by_id.get(old_id)
        if cit is None:
            return ""  # orphaned marker -> drop it
        new_id = len(new_citations) + 1
        renumbered = dict(cit)
        renumbered["citation_id"] = new_id
        new_citations.append(renumbered)
        return f"[{new_id}]"

    cleaned = re.sub(r"\[(\d+)\]", repl, answer)
    # Tidy whitespace left behind by removed markers ("text  ." -> "text.")
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned, new_citations


def generate_answer_with_citations(
        question: str,
        context: str,
        results: List[Any],
        llm_model: str,
        anthropic_api_key: str
    ) -> Dict[str, Any]:
    """Generate answer with structured citations using Anthropic Claude.

    Args:
        question: User's question
        context: Formatted context from source chunks
        results: Source chunks from Qdrant
        llm_model: Anthropic model name
        anthropic_api_key: Anthropic API key

    Returns:
        Dict with answer and validated citations
    """
    client = anthropic.Anthropic(api_key=anthropic_api_key)

    system_prompt = """Answer the user's question using ONLY the provided sources from 80,000 Hours articles.

        STEP 1: Write your answer
        - Write a clear, concise answer to the question
        - Use a natural, conversational tone
        - After EACH substantive claim, add a citation marker
        - The marker is a running counter: the first marker is ALWAYS [1], the
          second is ALWAYS [2], the third [3], and so on — strictly increasing by 1
        - NEVER reuse a number. Even when two claims come from the SAME source,
          they still get different, sequential numbers (e.g. [1] then [2]).
        - Example: "Career capital is important [1]. You can build it through work [2]."

        STEP 2: Provide citations
        - For each [N] in your answer, provide a citation with:
        * citation_id: The number from your answer (1 for [1], 2 for [2], etc.) - matches the marker exactly
        * source_id: Which source it came from (match the [Source N] label exactly)
        * quote: Copy the EXACT sentences from that source, word-for-word
        - citation_id is the position of the marker in your answer and is UNIQUE.
          source_id is the source the quote came from and MAY repeat across citations.

        EXAMPLE - two claims, both from [Source 3]:
        - Your answer: "Career capital helps you succeed [1]. It compounds over time [2]."
        - Your citations:
          {"citation_id": 1, "source_id": 3, "quote": "Career capital includes..."}
          {"citation_id": 2, "source_id": 3, "quote": "It compounds over time because..."}
          (Note: same source_id 3, but DIFFERENT sequential citation_ids 1 and 2.)

        CRITICAL RULES:
        1. citation_id is a strictly increasing counter starting at 1, incrementing by 1
           for every marker, with NO gaps and NO repeats - even for the same source.
        2. Copy quotes EXACTLY - No changes, NO ellipses, No paraphrasing
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
    response = client.messages.create(
        model=llm_model,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        output_config={"format": {"type": "json_schema", "schema": CITATION_SCHEMA}},
    )
    llm_time = (time.time() - llm_start) * 1000
    print(f"[TIMING] LLM call: {llm_time:.0f}ms")

    # output_config.format guarantees the first text block is valid JSON
    response_text = next(b.text for b in response.content if b.type == "text")

    # Parse LLM response
    parsed = parse_llm_response(response_text)
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

    # Drop in-text markers whose citation didn't survive validation and renumber
    # the rest, so every visible [N] is a real, clickable, sequential citation.
    answer, validated_citations = reconcile_citation_markers(
        answer, result["validated_citations"]
    )

    return {
        "answer": answer,
        "citations": validated_citations,
        "validation_errors": result["validation_errors"],
        "total_citations": len(citations),
        "valid_citations": len(validated_citations)
    }

# ============================================================================
# Results Processing & Display
# ============================================================================

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
    
    with open("/tmp/validation_results.json", "w", encoding="utf-8") as f:
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

# ============================================================================
# Main Public API
# ============================================================================

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
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    total_time = (time.time() - total_start) * 1000
    print(f"[TIMING] Total: {total_time:.0f}ms")
    
    # Display results
    # display_results(question, result, context if show_context else None)
    
    # Save debug output
    save_validation_results(question, result, results, 0)
    
    return {
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
        "validation_errors": result["validation_errors"],
        "sources": results
    }
