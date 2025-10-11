import json
import os
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from config import MODEL_NAME

BUFFER_SIZE = 3
BREAKPOINT_PERCENTILE_THRESHOLD = 87
NUMBER_OF_ARTICLES = 86
INPUT_FOLDER = "extracted_content"
OUTPUT_FILE = "chunks.jsonl"

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

def make_jsonl(articles, out_path="chunks.jsonl"):
    """Create JSONL with semantic chunks from multiple articles."""
    print("Loading embedding model for semantic chunking...")
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, article in enumerate(articles, 1):
            print(f"Chunking ({idx}/{len(articles)}): {article['title']}")
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

def chunk_from_json_files(input_folder=INPUT_FOLDER, output_file=OUTPUT_FILE):
    """Load articles from JSON files in folder and chunk them to JSONL."""
    if not os.path.exists(input_folder):
        print(f"Input folder '{input_folder}' not found")
        return
    
    # Load all articles from JSON files
    all_articles = []
    json_files = [f for f in os.listdir(input_folder) if f.endswith('.json')]
    
    if not json_files:
        print(f"No JSON files found in {input_folder}")
        return
    
    for json_file in json_files:
        json_path = os.path.join(input_folder, json_file)
        with open(json_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
            all_articles.extend(articles)
            print(f"Loaded {len(articles)} articles from {json_file}")
    
    if not all_articles:
        print("No articles found to chunk")
        return
    
    print(f"\nTotal articles to chunk: {len(all_articles)}")
    print("Loading embedding model for semantic chunking...")
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    
    chunk_count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for idx, article in enumerate(all_articles, 1):
            print(f"Chunking ({idx}/{len(all_articles)}): {article['title']}")
            chunks = chunk_text_semantic(article["text"], embed_model)
            for i, chunk in enumerate(chunks, 1):
                record = {
                    "url": article["url"],
                    "title": article["title"],
                    "date": article.get("date"),
                    "chunk_id": i,
                    "text": chunk,
                }
                chunk_count += 1
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n✓ Created {chunk_count} chunks from {len(all_articles)} articles")
    print(f"💾 Saved to {output_file}")

def main():
    articles = load_articles(n=NUMBER_OF_ARTICLES)
    if not articles:
        print("No articles found in articles.json")
        return

    make_jsonl(articles)
    print(f"Chunks from {len(articles)} articles written to chunks.jsonl")

if __name__ == "__main__":
    main()