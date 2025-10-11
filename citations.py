"""Citation validation and formatting for RAG system.

This module handles structured citations with validation to prevent hallucination.
"""

import json
from typing import List, Dict, Any
from urllib.parse import quote
from rapidfuzz import fuzz
from fuzzysearch import find_near_matches


FUZZY_THRESHOLD = 90

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
    # Take only the first line/paragraph (text fragments can't match across elements)
    first_line = quote_text.split('\n')[0].strip()
    
    # Remove bullet point markers (they're formatting, not content)
    if first_line.startswith('- '):
        first_line = first_line[2:].strip()
    
    # Extract a meaningful snippet (first ~80 chars work better for text fragments)
    # Cut at word boundaries to avoid breaking words mid-way
    max_length = 80
    if len(first_line) > max_length:
        # Find the last space before the cutoff
        text_fragment = first_line[:max_length]
        last_space = text_fragment.rfind(' ')
        if last_space > 0:  # If we found a space, cut there
            text_fragment = text_fragment[:last_space]
    else:
        text_fragment = first_line
    
    text_fragment = text_fragment.strip()
    
    encoded_text = quote(text_fragment, safe='')
    # Manually encode the unreserved chars that quote() preserves
    encoded_text = encoded_text.replace('-', '%2D')
    encoded_text = encoded_text.replace('.', '%2E')
    encoded_text = encoded_text.replace('_', '%5F')
    encoded_text = encoded_text.replace('~', '%7E')
    return f"{base_url}#:~:text={encoded_text}"

def parse_llm_response(response_content: str) -> Dict[str, Any]:
    """Parse and validate LLM JSON response.
    
    Args:
        response_content: Raw JSON string from LLM
        
    Returns:
        Dict with answer and citations, or error information
    """
    try:
        result = json.loads(response_content)
        # Enforce strict shape: must have 'answer' (str) and 'citations' (list of dicts)
        if not isinstance(result, dict) or 'answer' not in result or 'citations' not in result:
            return {
                "answer": response_content,
                "citations": [],
                "validation_errors": ["Response JSON missing required keys 'answer' and/or 'citations'."]
            }
        if not isinstance(result['answer'], str) or not isinstance(result['citations'], list):
            return {
                "answer": response_content,
                "citations": [],
                "validation_errors": ["Response JSON has incorrect types for 'answer' or 'citations'."]
            }
        return result
    except json.JSONDecodeError:
        return {
            "answer": response_content,
            "citations": [],
            "validation_errors": ["Failed to parse JSON response"]
        }

def build_citation_entry(citation: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a citation entry from validation result.
    
    Args:
        citation: Raw citation dict from LLM with citation_id, source_id, quote
        validation_result: Result from validate_citation()
        
    Returns:
        Complete citation entry with URL and metadata
    """
    matched_text = validation_result["matched_text"]
    highlighted_url = create_highlighted_url(
        validation_result["url"], 
        matched_text
    )
    citation_entry = {
        "citation_id": citation.get("citation_id", 0),
        "source_id": validation_result["source_id"],
        "quote": citation.get("quote", ""),  # AI's claimed quote
        "matched_text": matched_text,  # Actual text from source
        "title": validation_result["title"],
        "url": highlighted_url,
        "fuzzy_match_score": validation_result["fuzzy_match_score"],
        "remapped": validation_result.get("remapped", False)
    }
    return citation_entry

def process_citations(citations: List[Dict[str, Any]], source_chunks: List[Any]) -> Dict[str, Any]:
    """Validate and process a batch of citations.
    
    Args:
        citations: List of citation dicts from LLM
        source_chunks: List of source chunks from Qdrant
        
    Returns:
        Dict with validated_citations and validation_errors lists
    """
    validated_citations = []
    validation_errors = []
    
    for citation in citations:
        quote = citation.get("quote", "")
        source_id = citation.get("source_id", 0)
        citation_id = citation.get("citation_id", 0)
        
        validation_result = validate_citation(quote, source_chunks, source_id)
        
        if validation_result["valid"]:
            citation_entry = build_citation_entry(citation, validation_result)
            validated_citations.append(citation_entry)
        else:
            # Add citation_id to validation result for tracking
            validation_result["citation_id"] = citation_id
            validation_errors.append(validation_result)
    
    return {
        "validated_citations": validated_citations,
        "validation_errors": validation_errors
    }

def _build_valid_result(quote: str, chunk: Any, chunk_id: int, score: float, 
                        remapped: bool = False) -> Dict[str, Any]:
    """Build a valid citation result dict."""
    matched_substring = find_best_match_substring(quote, chunk.payload['text'])
    result = {
        "valid": True,
        "quote": quote,
        "matched_text": matched_substring,
        "source_id": chunk_id,
        "title": chunk.payload['title'],
        "url": chunk.payload['url'],
        "fuzzy_match_score": score
    }
    if remapped:
        result["remapped"] = True
    return result

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
        return _build_valid_result(quote, source_chunks[source_id - 1], source_id, claimed_score)
    
    # Step 2: Search all other sources for remapping
    for idx, chunk in enumerate(source_chunks, 1):
        if idx == source_id:
            continue  # Already checked
        score = fuzz.partial_ratio(quote, chunk.payload['text'])
        if score >= FUZZY_THRESHOLD:
            return _build_valid_result(quote, chunk, idx, score, remapped=True)
    
    # Validation failed - find closest match for debugging
    matched_text = find_best_match_substring(quote, source_text)
    return {
        "valid": False,
        "quote": quote,
        "source_id": source_id,
        "reason": f"Quote not found in any source (claimed source: {claimed_score:.1f}% fuzzy match)",
        "matched_text": matched_text,
        "fuzzy_match_score": claimed_score
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
        score = cit.get('fuzzy_match_score', 100)
        
        if cit.get('remapped'):
            note = f" ({score:.1f}% fuzzy match, remapped)"
        else:
            note = f" ({score:.1f}% fuzzy match)"
        
        citation_parts.append(
            f"{marker} {cit['title']}{note}\n"
            f"    URL: {cit['url']}\n"
            f"    Quote: \"{cit['quote']}\"\n"
        )
    return "\n".join(citation_parts)

