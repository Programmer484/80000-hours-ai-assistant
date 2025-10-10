# 80,000 Hours RAG System

## Setup

1. Install dependencies (create `requirements.txt` if needed)
2. Create `.env` file with:
   ```
   QDRANT_URL=your_url
   QDRANT_API_KEY=your_key
   OPENAI_API_KEY=your_key
   ```

## Usage

### First Time Setup (run in order):

1. **Extract articles** → `extract_articles_cli.py`
   - Scrapes 80k Hours articles from sitemap
   - Only needed once (or to refresh content)
   - Saves to a json file

2. **Chunk articles** → `chunk_articles_cli.py`
   - Splits articles into chunks
   - Skip if `article_chunks.jsonl` already exists

3. **Upload to Qdrant** → `upload_to_qdrant_cli.py`
   - Generates embeddings and uploads to vector DB
   - Only needed once (or to rebuild index)

### Query the System:

**Web Interface (Recommended):**
```bash
python web_app.py
```
Then open http://localhost:7860 in your browser.

**Command Line:**
```bash
python rag_chat.py "your question here"
python rag_chat.py "your question" --show-context
```

## Files

- `extract_articles_cli.py` - Scrapes articles
- `chunk_articles_cli.py` - Creates chunks
- `upload_to_qdrant_cli.py` - Uploads to Qdrant
- `rag_chat.py` - CLI query interface
- `web_app.py` - Web interface (Gradio)
- `citation_validator.py` - Validates LLM citations

## Deployment

**Local:** Just run `python web_app.py`

**Public sharing:** Set `share=True` in `web_app.py` to get a temporary public URL

**Production hosting:** Deploy to:
- Hugging Face Spaces (free tier available)
- Gradio Cloud
- Any cloud service (AWS, GCP, Azure) with Python support
