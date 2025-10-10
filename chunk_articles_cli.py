import json
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from config import MODEL_NAME

BUFFER_SIZE = 3
BREAKPOINT_PERCENTILE_THRESHOLD = 87
NUMBER_OF_ARTICLES = 1

def load_articles(json_path="articles.json", n=None):
    """Load articles from JSON file. Optionally load only first N articles."""
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    return articles[:n] if n else articles

def chunk_text_semantic(text, embed_model):
    """Chunk text using semantic similarity with sentence buffer for overlap."""
    splitter = SemanticSplitterNodeParser(
        embed_model=embed_model,
        buffer_size=BUFFER_SIZE,
        breakpoint_percentile_threshold=BREAKPOINT_PERCENTILE_THRESHOLD
    )
    doc = Document(text=text)
    nodes = splitter.get_nodes_from_documents([doc])
    return [node.text for node in nodes]

def make_jsonl(articles, out_path="article_chunks.jsonl"):
    """Create JSONL with semantic chunks from multiple articles."""
    print("Loading embedding model for semantic chunking...")
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for article in articles:
            print(f"Chunking: {article['title']}")
            chunks = chunk_text_semantic(article["text"], embed_model)
            for i, chunk in enumerate(chunks, 1):
                record = {
                    "url": article["url"],
                    "title": article["title"],
                    "date": article.get("date"),
                    "chunk_id": i,
                    "text": chunk,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

def main():
    articles = load_articles(n=NUMBER_OF_ARTICLES)
    if not articles:
        print("No articles found in articles.json")
        return

    make_jsonl(articles)
    print(f"Chunks from {len(articles)} articles written to article_chunks.jsonl")

if __name__ == "__main__":
    main()