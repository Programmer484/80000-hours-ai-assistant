---
title: 80,000 Hours RAG Q&A
emoji: 🎯
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---

# 🎯 80,000 Hours Career Advice Q&A

A Retrieval-Augmented Generation (RAG) system that answers career-related questions using content from [80,000 Hours](https://80000hours.org/), with validated citations.

## Features

- 🔍 **Semantic Search**: Retrieves relevant content from 80,000 Hours articles
- 🤖 **AI-Powered Answers**: Uses GPT-4o-mini to generate comprehensive responses
- ✅ **Citation Validation**: Automatically validates that quotes exist in source material
- 📚 **Source Attribution**: Every answer includes validated citations with URLs

## How It Works

1. Your question is converted to a vector embedding
2. Relevant article chunks are retrieved from Qdrant vector database
3. GPT-4o-mini generates an answer with citations
4. Citations are validated against source material
5. You get an answer with verified quotes and source links

## Configuration for Hugging Face Spaces

To deploy this app, you need to configure the following **Secrets** in your Space settings:

1. Go to your Space → Settings → Variables and Secrets
2. Add these secrets:
   - `QDRANT_URL`: Your Qdrant cloud instance URL
   - `QDRANT_API_KEY`: Your Qdrant API key
   - `OPENAI_API_KEY`: Your OpenAI API key

## Local Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with:
```
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### First Time Setup (run in order):

1. **Extract articles** → `python extract_articles_cli.py`
   - Scrapes 80,000 Hours articles from sitemap
   - Only needed once (or to refresh content)

2. **Chunk articles** → `python chunk_articles_cli.py`
   - Splits articles into semantic chunks

3. **Upload to Qdrant** → `python upload_to_qdrant_cli.py`
   - Generates embeddings and uploads to vector DB

### Running Locally

**Web Interface:**
```bash
python app.py
```

**Command Line:**
```bash
python rag_chat.py "your question here"
python rag_chat.py "your question" --show-context
```

## Project Structure

- `app.py` - Main Gradio web interface
- `rag_chat.py` - RAG logic and CLI interface
- `citation_validator.py` - Citation validation system
- `extract_articles_cli.py` - Article scraper
- `chunk_articles_cli.py` - Article chunking
- `upload_to_qdrant_cli.py` - Vector DB uploader
- `config.py` - Shared configuration

## Tech Stack

- **Frontend**: Gradio 4.0+
- **LLM**: OpenAI GPT-4o-mini
- **Vector DB**: Qdrant Cloud
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Citation Validation**: rapidfuzz for fuzzy matching

## Credits

Content sourced from [80,000 Hours](https://80000hours.org/), a nonprofit that provides research and support to help people find careers that effectively tackle the world's most pressing problems.
