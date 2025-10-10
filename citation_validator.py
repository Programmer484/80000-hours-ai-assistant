"""Citation validation and formatting for RAG system.

This module handles structured citations with validation to prevent hallucination.
"""

import json
import time
from typing import List, Dict, Any
from urllib.parse import quote
from openai import OpenAI
from rapidfuzz import fuzz, process
from fuzzysearch import find_near_matches


FUZZY_THRESHOLD = 95

def find_best_match_substring(quote: str, source_text: str) -> str:
    """Find the actual matching substring in source_text.
    
    Uses fuzzysearch to find where the quote matches and extract that exact substring.
    
    Args:
        quote: The text to find
        source_text: The text to search in
        
    Returns:
        The matching substring from source_text
    """
    # Use fuzzysearch to find near matches directly in the original text
    # max_l_dist is the maximum Levenshtein distance (edits) allowed
    max_dist = max(2, len(quote) // 15)  # Allow ~6-7% character differences
    
    try:
        # Search directly - fuzzysearch handles minor differences like quote types
        matches = find_near_matches(quote, source_text, max_l_dist=max_dist)
        
        if matches:
            # Get the best match (first one, they're sorted by quality)
            best_match = matches[0]
            # Extract from the original source_text with exact punctuation
            return source_text[best_match.start:best_match.end].strip()
    except:
        pass
    
    # Fallback: return the quote if no match found
    return quote


def create_highlighted_url(base_url: str, quote_text: str) -> str:
    """Create a URL with text fragment that highlights the quoted text.
    
    Uses the :~:text= URL fragment feature to scroll to and highlight text.
    
    Args:
        base_url: The base article URL
        quote_text: The text to highlight (should be the exact text from source)
        
    Returns:
        URL with text fragment
    """
    # Extract a meaningful snippet (first ~80 chars work better for text fragments)
    # Cut at word boundaries to avoid breaking words mid-way
    max_length = 80
    if len(quote_text) > max_length:
        # Find the last space before the cutoff
        text_fragment = quote_text[:max_length]
        last_space = text_fragment.rfind(' ')
        if last_space > 0:  # If we found a space, cut there
            text_fragment = text_fragment[:last_space]
    else:
        text_fragment = quote_text
    
    text_fragment = text_fragment.strip()
    
    # Encode everything for maximum compatibility
    # quote() with safe='' still preserves unreserved chars (- . _ ~)
    # So we manually encode those too
    encoded_text = quote(text_fragment, safe='')
    # Manually encode the unreserved chars that quote() preserves
    encoded_text = encoded_text.replace('-', '%2D')
    encoded_text = encoded_text.replace('.', '%2E')
    encoded_text = encoded_text.replace('_', '%5F')
    encoded_text = encoded_text.replace('~', '%7E')
    return f"{base_url}#:~:text={encoded_text}"

def validate_citation(quote: str, source_chunks: List[Any], source_id: int) -> Dict[str, Any]:
    """Validate that a quote exists in the specified source chunk.
    
    Args:
        quote: The quoted text to validate
        source_chunks: List of source chunks from Qdrant
        source_id: 1-indexed source ID
        
    Returns:
        Dict with validation result and metadata
    """
    if source_id < 1 or source_id > len(source_chunks):
        return {
            "valid": False,
            "quote": quote,
            "source_id": source_id,
            "reason": "Invalid source ID",
            "source_text": None
        }
    

    
    # Step 1: Check claimed source first (fast path)
    source_text = source_chunks[source_id - 1].payload['text']
    claimed_score = fuzz.partial_ratio(quote, source_text)
    
    if claimed_score >= FUZZY_THRESHOLD:
        # Find the actual matching substring in the source
        matched_substring = find_best_match_substring(quote, source_chunks[source_id - 1].payload['text'])
        return {
            "valid": True,
            "quote": quote,
            "matched_text": matched_substring,  # The actual matching text from 80k Hours
            "source_id": source_id,
            "title": source_chunks[source_id - 1].payload['title'],
            "url": source_chunks[source_id - 1].payload['url'],
            "similarity_score": claimed_score
        }
    
    for idx, chunk in enumerate(source_chunks, 1):
        if idx == source_id:
            continue  # Already checked
        score = fuzz.partial_ratio(quote, chunk.payload['text'])
        if score >= FUZZY_THRESHOLD:
            # Find the actual matching substring in the source
            matched_substring = find_best_match_substring(quote, chunk.payload['text'])
            return {
                "valid": True,
                "quote": quote,
                "matched_text": matched_substring,  # The actual matching text from 80k Hours
                "source_id": idx,
                "title": chunk.payload['title'],
                "url": chunk.payload['url'],
                "similarity_score": score,
                "remapped": True,
                "original_source_id": source_id
            }
    
    # Validation failed - report best score from claimed source
    return {
        "valid": False,
        "quote": quote,
        "source_id": source_id,
        "reason": f"Quote not found in any source (claimed source: {claimed_score:.1f}% similarity)",
        "source_text": source_chunks[source_id - 1].payload['text']
    }


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
  * source_id: Which source it came from (see [Source N] in context below)
  * quote: Copy the EXACT sentences from that source, word-for-word

CRITICAL RULES:
1. Number citations in ORDER: [1] is first, [2] is second, [3] is third, etc.
2. Copy quotes EXACTLY - no changes, no ellipses, no paraphrasing
3. Match source_id to where you found the quote ([Source 1] → source_id: 1)
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

    llm_call_start = time.time()
    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    print(f"[TIMING] OpenAI call: {(time.time() - llm_call_start)*1000:.2f}ms")
    
    # Parse the JSON response
    try:
        result = json.loads(response.choices[0].message.content)
        # Enforce strict shape: must have 'answer' (str) and 'citations' (list of dicts)
        if not isinstance(result, dict) or 'answer' not in result or 'citations' not in result:
            return {
                "answer": response.choices[0].message.content,
                "citations": [],
                "validation_errors": ["Response JSON missing required keys 'answer' and/or 'citations'."]
            }
        if not isinstance(result['answer'], str) or not isinstance(result['citations'], list):
            return {
                "answer": response.choices[0].message.content,
                "citations": [],
                "validation_errors": ["Response JSON has incorrect types for 'answer' or 'citations'."]
            }
        answer = result.get("answer", "")
        citations = result.get("citations", [])
    except json.JSONDecodeError:
        return {
            "answer": response.choices[0].message.content,
            "citations": [],
            "validation_errors": ["Failed to parse JSON response"]
        }
    

    # Validate each citation
    validation_start = time.time()
    validated_citations = []
    validation_errors = []
    
    for citation in citations:
        quote = citation.get("quote", "")
        source_id = citation.get("source_id", 0)
        citation_id = citation.get("citation_id", 0)
        
        validation_result = validate_citation(quote, results, source_id)
        
        if validation_result["valid"]:
            # Create URL with text fragment to highlight the matched text
            matched_text = validation_result.get("matched_text", quote)
            highlighted_url = create_highlighted_url(
                validation_result["url"], 
                matched_text
            )
            citation_entry = {
                "citation_id": citation_id,
                "source_id": validation_result["source_id"],
                "quote": quote,  # AI's claimed quote
                "matched_text": matched_text,  # Actual text from source
                "title": validation_result["title"],
                "url": highlighted_url,
                "similarity_score": validation_result["similarity_score"]
            }
            if validation_result.get("remapped"):
                citation_entry["remapped_from"] = validation_result["original_source_id"]
            validated_citations.append(citation_entry)
        else:
            validation_errors.append({
                "citation_id": citation_id,
                "reason": validation_result['reason'],
                "claimed_quote": quote,
                "source_text": validation_result.get('source_text')
            })
    
    print(f"[TIMING] Validation: {(time.time() - validation_start)*1000:.2f}ms")
    
    return {
        "answer": answer,
        "citations": validated_citations,
        "validation_errors": validation_errors,
        "total_citations": len(citations),
        "valid_citations": len(validated_citations)
    }


def format_citations_display(citations: List[Dict[str, Any]]) -> str:
    """Format validated citations in order with article title, URL, and quoted text.
    
    Args:
        citations: List of validated citation dicts
        
    Returns:
        Formatted string for display
    """
    if not citations:
        return "No citations available."
    
    # Sort citations by citation_id to display in order
    sorted_citations = sorted(citations, key=lambda x: x.get('citation_id', 0))
    
    citation_parts = []
    for cit in sorted_citations:
        marker = f"[{cit['citation_id']}]"
        score = cit.get('similarity_score', 100)
        
        if cit.get('remapped_from'):
            note = f" ({score:.1f}% match, remapped: source {cit['remapped_from']} → {cit['source_id']})"
        else:
            note = f" ({score:.1f}% match)"
        
        citation_parts.append(
            f"{marker} {cit['title']}{note}\n"
            f"    URL: {cit['url']}\n"
            f"    Quote: \"{cit['quote']}\"\n"
        )
    return "\n".join(citation_parts)

