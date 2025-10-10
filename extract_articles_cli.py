import requests, re, json
import trafilatura
from typing import List, Dict, Optional

HEADERS = {"User-Agent": "RAG-80k/0.1 (+your-contact)"}
NUMBER_OF_ARTICLES = 10

def get_all_article_urls() -> List[str]:
    """Extract all article URLs from the sitemap."""
    sitemap_url = "https://80000hours.org/article-sitemap.xml"
    r = requests.get(sitemap_url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    
    # Find all <loc> tags in the sitemap
    urls = re.findall(r"<loc>(.*?)</loc>", r.text)
    return urls

def extract_article(url: str) -> Optional[Dict]:
    """Extract article content and metadata from a URL."""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = trafilatura.extract(
        r.content,
        url=url,
        with_metadata=True,
        include_links=False,
        include_comments=False,
        include_formatting=False,
        output_format="json",
    )
    return json.loads(data) if data else None

def extract_all_articles() -> List[Dict]:
    """Extract all articles from the sitemap."""
    urls = get_all_article_urls()
    print(f"Found {len(urls)} articles in sitemap")
    
    articles = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Extracting: {url}")
        record = extract_article(url)
        if record and record.get("text"):
            articles.append({
                "url": url,
                "title": record.get("title", ""),
                "date": record.get("date"),
                "text": record.get("text", "").strip()
            })
        else:
            print(f"  Failed to extract: {url}")
    
    print(f"Successfully extracted {len(articles)} articles")
    return articles

def extract_first_n_articles(n: int) -> List[Dict]:
    """Extract the first N articles from the sitemap."""
    urls = get_all_article_urls()[:n]
    print(f"Extracting first {n} articles")
    
    articles = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Extracting: {url}")
        record = extract_article(url)
        if record and record.get("text"):
            articles.append({
                "url": url,
                "title": record.get("title", ""),
                "date": record.get("date"),
                "text": record.get("text", "").strip()
            })
        else:
            print(f"  Failed to extract: {url}")
    
    print(f"Successfully extracted {len(articles)} articles")
    return articles

def main():
    articles = extract_all_articles()
    
    if articles:
        # Save to JSON file
        output_file = "articles.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
