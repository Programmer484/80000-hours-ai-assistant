#!/usr/bin/env python3
"""Simple test for create_highlighted_url function."""

from urllib.parse import urlparse
from citations import create_highlighted_url

def extract_base_url(full_url: str) -> str:
    """Extract base URL without fragments."""
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

# Paste your URL and text here
full_url = "https://80000hours.org/articles/future-generations/"
quote_text = '''- Risks from'''

base_url = extract_base_url(full_url)
result = create_highlighted_url(base_url, quote_text)
print(result)