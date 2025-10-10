# Hugging Face Spaces Deployment Checklist

## ✅ Files Ready for Upload

These are the ONLY files you need to upload to Hugging Face Spaces:

- [ ] `app.py` - Main Gradio interface (✓ Created)
- [ ] `rag_chat.py` - RAG logic
- [ ] `citation_validator.py` - Citation validation
- [ ] `config.py` - Configuration constants
- [ ] `requirements.txt` - Python dependencies (✓ Updated)
- [ ] `README.md` - Documentation with HF metadata (✓ Updated)

## ❌ Files to EXCLUDE (Do NOT upload)

- `.env` - Contains secrets (use HF Spaces Secrets instead)
- `articles.json` - Large data file (not needed, data is in Qdrant)
- `article_chunks.jsonl` - Large data file (not needed, data is in Qdrant)
- `validation_results.json` - Runtime output file
- `__pycache__/` - Python cache
- `web_app.py` - Old version (replaced by app.py)
- `extract_articles_cli.py` - Setup script (not needed for deployed app)
- `chunk_articles_cli.py` - Setup script (not needed for deployed app)
- `upload_to_qdrant_cli.py` - Setup script (not needed for deployed app)

## 🔧 Pre-Deployment Steps

### 1. Verify Data is in Qdrant
```bash
# Make sure you've already run these locally:
python extract_articles_cli.py
python chunk_articles_cli.py
python upload_to_qdrant_cli.py
```

### 2. Test Locally (Optional)
```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

### 3. Create Hugging Face Space
1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Configure:
   - **Space name**: Your choice (e.g., `80k-career-advisor`)
   - **SDK**: Gradio
   - **Hardware**: CPU basic (free tier is sufficient)
   - **Visibility**: Public or Private

### 4. Configure Secrets (CRITICAL!)
In your Space Settings → Variables and Secrets, add:

- **QDRANT_URL**: `https://your-cluster-url.aws.cloud.qdrant.io`
- **QDRANT_API_KEY**: `your-qdrant-api-key`
- **OPENAI_API_KEY**: `sk-...your-openai-key`

### 5. Upload Files

**Option A: Git**
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# Copy only the necessary files
cp /home/ryan/Documents/80k_rag/app.py .
cp /home/ryan/Documents/80k_rag/rag_chat.py .
cp /home/ryan/Documents/80k_rag/citation_validator.py .
cp /home/ryan/Documents/80k_rag/config.py .
cp /home/ryan/Documents/80k_rag/requirements.txt .
cp /home/ryan/Documents/80k_rag/README.md .

git add .
git commit -m "Initial deployment"
git push
```

**Option B: Web Interface**
1. Click "Files and versions" tab
2. Click "Upload files"
3. Drag and drop the 6 files listed above
4. Click "Commit"

### 6. Monitor Build
- Watch the build logs in the App tab
- Build typically takes 2-5 minutes
- Look for any errors in dependencies or imports

## 🚀 Post-Deployment

### Testing
1. Visit your Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
2. Try the example questions
3. Test with a custom question
4. Verify citations are displaying correctly

### Common Issues

**Problem**: Build fails with "Module not found"
- **Solution**: Check that all imports in `app.py`, `rag_chat.py`, and `citation_validator.py` are in `requirements.txt`

**Problem**: Runtime error about missing API keys
- **Solution**: Verify secrets are set correctly in Space Settings

**Problem**: Slow responses
- **Solution**: Consider upgrading to a better hardware tier

**Problem**: "No relevant sources found"
- **Solution**: Verify your Qdrant instance is accessible and contains data

## 📊 Estimated Costs

- **HF Space (CPU basic)**: Free
- **OpenAI API**: ~$0.01-0.05 per query (GPT-4o-mini)
- **Qdrant Cloud**: Free tier supports up to 1GB

## 🔄 Updating Your Deployed App

```bash
# Make changes locally
# Then push updates
cd YOUR_SPACE_NAME
git add .
git commit -m "Update: description of changes"
git push
```

## 📝 Notes

- The app will save `validation_results.json` during runtime (this is fine, stored in Space's temporary storage)
- Secrets in HF Spaces are injected as environment variables (compatible with your code)
- The `.env` file is only for local development

