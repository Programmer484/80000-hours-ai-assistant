# Deploying to Hugging Face Spaces

## Prerequisites

1. A Hugging Face account (sign up at https://huggingface.co/)
2. Qdrant Cloud instance with your data uploaded
3. OpenAI API key

## Step-by-Step Deployment

### 1. Create a New Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in the details:
   - **Owner**: Your username or organization
   - **Space name**: `80k-rag-qa` (or your preferred name)
   - **License**: Choose appropriate license (e.g., MIT)
   - **Space SDK**: Select **"Gradio"**
   - **Hardware**: Select **"CPU basic"** (free tier) or upgrade if needed
   - **Visibility**: Choose "Public" or "Private"
4. Click **"Create Space"**

### 2. Configure Secrets

Before uploading code, set up your API keys:

1. Go to your Space's page
2. Click **"Settings"** → **"Variables and Secrets"**
3. Click **"New Secret"** for each of the following:
   - **Name**: `QDRANT_URL` | **Value**: Your Qdrant instance URL
   - **Name**: `QDRANT_API_KEY` | **Value**: Your Qdrant API key
   - **Name**: `OPENAI_API_KEY` | **Value**: Your OpenAI API key
4. Click **"Save"** for each secret

### 3. Upload Your Code

**Option A: Using Git (Recommended)**

```bash
# Clone your new Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# Copy necessary files from this project
cp /home/ryan/Documents/80k_rag/app.py .
cp /home/ryan/Documents/80k_rag/rag_chat.py .
cp /home/ryan/Documents/80k_rag/citation_validator.py .
cp /home/ryan/Documents/80k_rag/config.py .
cp /home/ryan/Documents/80k_rag/requirements.txt .
cp /home/ryan/Documents/80k_rag/README.md .

# Add, commit, and push
git add .
git commit -m "Initial deployment"
git push
```

**Option B: Using the Web Interface**

1. Go to your Space → **"Files and versions"** tab
2. Click **"Add file"** → **"Upload files"**
3. Upload these files:
   - `app.py`
   - `rag_chat.py`
   - `citation_validator.py`
   - `config.py`
   - `requirements.txt`
   - `README.md`
4. Click **"Commit changes to main"**

### 4. Monitor Deployment

1. Go to the **"App"** tab to see your Space building
2. Check the **"Logs"** section (click "See logs" if build fails)
3. Wait for the build to complete (usually 2-5 minutes)
4. Your app will be live at: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`

## Troubleshooting

### Build Fails
- Check the logs for missing dependencies
- Ensure all required files are uploaded
- Verify `requirements.txt` has correct package names

### Runtime Errors
- Verify secrets are set correctly in Settings
- Check logs for import errors or missing modules
- Ensure your Qdrant instance is accessible

### Out of Memory
- Consider upgrading to a larger hardware tier
- Optimize model loading and caching
- Reduce `SOURCE_COUNT` in `rag_chat.py`

## Updating Your Space

To update your deployed app:

```bash
# Make changes to your local files
# Then push updates
git add .
git commit -m "Update: describe your changes"
git push
```

The Space will automatically rebuild with your changes.

## Cost Considerations

- **Hugging Face Space**: Free for CPU basic tier
- **OpenAI API**: Pay per token (GPT-4o-mini is cost-effective)
- **Qdrant Cloud**: Has free tier, pay for larger datasets
- **Estimated cost**: ~$0.01-0.10 per query depending on usage

## Security Notes

- Never commit API keys to git (they should only be in Space Secrets)
- Use `.gitignore` to exclude sensitive files
- Regularly rotate API keys
- Monitor API usage to prevent abuse

