import requests, re, json
import trafilatura
from typing import List, Dict, Optional
from time import sleep
from dateutil import parser as date_parser
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import os
import threading
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Parallel processing settings
USE_PARALLEL = True
MAX_WORKERS = 3

# Rate limiting settings
MIN_DELAY = 1.0
MAX_DELAY = 3.0
RATE_LOCK = threading.Lock()
_next_request_time = 0.0

# Output settings
OUTPUT_FOLDER = "extracted_content"
TEST_LIMIT = None

# HTTP settings
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# All content sitemaps (excluding category/author which are just metadata)
SITEMAPS = {
    "ai_career_guide_pages": "https://80000hours.org/ai_career_guide_page-sitemap.xml",
    # "articles": "https://80000hours.org/article-sitemap.xml",
    # "career_guide_pages": "https://80000hours.org/careerguidepage-sitemap.xml",
    "career_profiles": "https://80000hours.org/career_profile-sitemap.xml",
    # "career_reports": "https://80000hours.org/career_report-sitemap.xml",
    # "case_studies": "https://80000hours.org/case_study-sitemap.xml",
    "posts": "https://80000hours.org/post-sitemap.xml",
    "problem_profiles": "https://80000hours.org/problem_profile-sitemap.xml",
    # "podcasts": "https://80000hours.org/podcast-sitemap.xml",
    # "podcast_after_hours": "https://80000hours.org/podcast_after_hours-sitemap.xml",
    "skill_sets": "https://80000hours.org/skill_set-sitemap.xml",
    # "videos": "https://80000hours.org/video-sitemap.xml",
}

# Thread-local session with retries and backoff
thread_local = threading.local()

def get_session():
    """Get or create a thread-local requests session with retries and connection pooling."""
    s = getattr(thread_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        retry = Retry(
            total=5, connect=3, read=3, status=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET", "HEAD"},
            backoff_factor=0.8,
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=MAX_WORKERS * 2,
            pool_maxsize=MAX_WORKERS * 2,
        )
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        thread_local.session = s
    return s

def throttle():
    """Enforce rate limiting across all threads."""
    global _next_request_time
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    with RATE_LOCK:
        now = time.monotonic()
        wait = max(0.0, _next_request_time - now)
        _next_request_time = max(now, _next_request_time) + delay
    if wait > 0:
        time.sleep(wait)

def get_urls_from_sitemap(sitemap_url: str) -> List[str]:
    """Extract all URLs from a sitemap."""
    throttle()
    r = get_session().get(sitemap_url, timeout=20)
    r.raise_for_status()
    return re.findall(r"<loc>(.*?)</loc>", r.text)

def parse_custom_date(html_content: str) -> Optional[str]:
    """
    Extract and parse publication date from 80,000 Hours HTML content.
    
    Priority:
    1. "Updated [date]" if present
    2. "Published [date]" otherwise
    
    Returns date in YYYY-MM-DD format, or None if not found.
    """
    # Date pattern: month + optional day (with ordinal) + year
    date_pattern = r'([A-Za-z]+\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?\d{4})'
    
    # Try "Updated" first, then "Published"
    for keyword in ['Updated', 'Published']:
        match = re.search(f'{keyword}\\s+{date_pattern}', html_content, re.IGNORECASE)
        if match:
            try:
                parsed_date = date_parser.parse(match.group(1), fuzzy=True)
                return parsed_date.strftime('%Y-%m-%d')
            except:
                pass
    
    return None

def extract_content(url: str) -> Optional[Dict]:
    """Extract content and metadata from a URL."""
    try:
        throttle()
        r = get_session().get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return None
    
    data = trafilatura.extract(
        r.content, url=url, with_metadata=True, 
        include_links=False, include_comments=False, 
        include_formatting=False, output_format="json"
    )
    
    if not data:
        return None
    
    result = json.loads(data)
    if custom_date := parse_custom_date(r.text):
        result['date'] = custom_date
    
    return result


def process_record(record: Optional[Dict], url: str, sitemap_name: str) -> Optional[Dict]:
    """Convert extraction record to final output format."""
    if not (record and record.get("text")):
        return None
    return {
        "url": url,
        "title": record.get("title", ""),
        "date": record.get("date"),
        "author": record.get("author"),
        "text": record.get("text", "").strip(),
        "content_type": sitemap_name
    }

def handle_extraction_result(record: Optional[Dict], url: str, sitemap_name: str, index: int, total: int, items: List[Dict]) -> None:
    """Process extraction result and add to items list if successful."""
    try:
        result = process_record(record, url, sitemap_name)
        if result:
            items.append(result)
        status = "✓" if result else "⚠️  Failed:"
        print(f"[{index}/{total}] {status} {url}")
    except Exception as e:
        print(f"[{index}/{total}] ❌ {url}: {e}")

def extract_from_sitemap(sitemap_name: str, sitemap_url: str, limit: int = None, parallel: bool = True, max_workers: int = 5) -> List[Dict]:
    """Extract content from a sitemap using either parallel or sequential processing."""
    print(f"\n{'='*80}")
    print(f"Processing {sitemap_name}...")
    print(f"{'='*80}")
    
    urls = get_urls_from_sitemap(sitemap_url)
    print(f"Found {len(urls)} URLs in sitemap")
    
    if limit:
        urls = urls[:limit]
        print(f"Limiting to first {limit} URL(s)")
    
    items = []
    
    if parallel and len(urls) > 1:
        print(f"🚀 Using parallel processing with {max_workers} workers")
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(extract_content, url): url 
                for url in urls
            }
            
            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                completed += 1
                handle_extraction_result(future.result(), url, sitemap_name, completed, len(urls), items)
    else:
        print("📝 Using sequential processing")
        for i, url in enumerate(urls, 1):
            handle_extraction_result(extract_content(url), url, sitemap_name, i, len(urls), items)
    
    print(f"✓ Successfully extracted {len(items)}/{len(urls)} items")
    return items

def extract_all_to_json():
    """Extract all content from sitemaps and save to individual JSON files."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    print("Starting 80,000 Hours content extraction...")
    print(f"Total content types: {len(SITEMAPS)}")
    print(f"Output folder: {OUTPUT_FOLDER}/")
    if TEST_LIMIT:
        print(f"⚠️  TEST MODE: Extracting only {TEST_LIMIT} item(s) per content type\n")
    
    all_stats = {}
    for content_type, sitemap_url in SITEMAPS.items():
        items = extract_from_sitemap(
            content_type, sitemap_url, 
            limit=TEST_LIMIT, parallel=USE_PARALLEL, max_workers=MAX_WORKERS
        )
        all_stats[content_type] = len(items)
        
        if items:
            output_file = os.path.join(OUTPUT_FOLDER, f"{content_type}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved to {output_file}")
    
    print(f"\n{'='*80}\nEXTRACTION COMPLETE\n{'='*80}")
    print(f"Total items extracted: {sum(all_stats.values())}")
    print("\nBreakdown by content type:")
    for content_type, count in sorted(all_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {content_type:25s}: {count:4d} items → {OUTPUT_FOLDER}/{content_type}.json")

def main():
    extract_all_to_json()

if __name__ == "__main__":
    main()

