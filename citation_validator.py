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
    # Normalize quote for better matching, but search directly in original source
    quote_norm = normalize_text(quote)
    
    # Use fuzzysearch to find near matches in the ORIGINAL text
    # This preserves punctuation and exact formatting
    # max_l_dist is the maximum Levenshtein distance (edits) allowed
    max_dist = max(2, len(quote_norm) // 15)  # Allow ~6-7% character differences
    
    try:
        # Search in the original source text (case-insensitive but preserves punctuation)
        matches = find_near_matches(quote_norm, source_text, max_l_dist=max_dist)
        
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
        quote_text: The text to highlight
        
    Returns:
        URL with text fragment
    """
    # Take first ~100 characters of quote for the URL (browsers have limits)
    # and clean up for URL encoding
    text_fragment = quote_text[:100].strip()
    encoded_text = quote(text_fragment)
    return f"{base_url}#:~:text={encoded_text}"


def normalize_text(text: str) -> str:
    """Normalize text for comparison by handling whitespace and punctuation variants."""
    # Normalize different dash types to standard hyphen
    text = text.replace('–', '-')  # en-dash
    text = text.replace('—', '-')  # em-dash
    text = text.replace('−', '-')  # minus sign
    # Normalize different apostrophe/quote types to standard ASCII
    text = text.replace(''', "'")  # curly apostrophe
    text = text.replace(''', "'")  # left single quote
    text = text.replace('"', '"')  # left double quote
    text = text.replace('"', '"')  # right double quote
    # Normalize whitespace
    text = " ".join(text.split())
    return text


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
    
    quote_clean = normalize_text(quote).lower()

    
    # Step 1: Check claimed source first (fast path)
    source_text = normalize_text(source_chunks[source_id - 1].payload['text']).lower()
    claimed_score = fuzz.partial_ratio(quote_clean, source_text)
    
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
        chunk_text = normalize_text(chunk.payload['text']).lower()
        score = fuzz.partial_ratio(quote_clean, chunk_text)
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
    
    system_prompt = """You are a helpful assistant that answers questions based on 80,000 Hours articles.

You MUST return your response in valid JSON format with this exact structure:
{
  "answer": "Your conversational answer with inline citation markers like [1], [2]",
  "citations": [
    {
      "citation_id": 1,
      "source_id": 1,
      "quote": "exact sentence or sentences from the source that support your claim"
    }
  ]
}

CITATION HARD RULES:
1. Copy quotes EXACTLY as they appear in the provided context
   - NO ellipses (...)
   - NO paraphrasing
   - NO punctuation changes
   - Word-for-word, character-for-character accuracy required

2. If the needed support is in two places, use TWO SEPARATE citation entries
   - Do NOT combine quotes from different sources or different parts of text
   - Each citation must contain a continuous, unmodified quote

3. Use the CORRECT source_id from the provided list
   - Source IDs are numbered [Source 1], [Source 2], etc. in the context
   - Verify the source_id matches where you found the quote

CRITICAL RULES FOR CITATIONS:
- For EVERY claim (advice, fact, statistic, recommendation), add an inline citation [1], [2], etc.
- For each citation, extract and quote the EXACT sentence(s) from the source that directly support your claim
- Find the specific sentence(s) in the source that contain the relevant information
- Each quote should be at least 20 characters and contain complete sentence(s)
- Multiple consecutive sentences can be quoted if needed to fully support the claim

WRITING STYLE:
- Write concisely in a natural, conversational tone
- You may paraphrase information in your answer, but always cite the source with exact quotes
- You can add brief context/transitions without citations, but cite all substantive claims
- If the sources don't fully answer the question, acknowledge that briefly
- Only use information from the provided sources - don't add external knowledge

EXAMPLES:

Example 1 - Single claim:
{
  "answer": "One of the most effective ways to build career capital is to work at a high-performing organization where you can learn from talented colleagues [1].",
  "citations": [
    {
      "citation_id": 1,
      "source_id": 2,
      "quote": "Working at a high-performing organization is one of the fastest ways to build career capital because you learn from talented colleagues and develop strong professional networks."
    }
  ]
}

Example 2 - Multiple claims:
{
  "answer": "AI safety is considered one of the most pressing problems of our time [1]. Experts estimate that advanced AI could be developed within the next few decades [2], and there's a significant talent gap in the field [3]. This means your contributions could have an outsized impact.",
  "citations": [
    {
      "citation_id": 1,
      "source_id": 1,
      "quote": "We believe that risks from artificial intelligence are one of the most pressing problems facing humanity today."
    },
    {
      "citation_id": 2,
      "source_id": 1,
      "quote": "Many AI researchers believe there's a 10-50% chance of human-level AI being developed by 2050."
    },
    {
      "citation_id": 3,
      "source_id": 3,
      "quote": "There are currently fewer than 300 people working full-time on technical AI safety research, despite the field's critical importance."
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

