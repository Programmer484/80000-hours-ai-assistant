# 🚀 Quick Start: Deploy to Hugging Face Spaces

## TL;DR - 5 Minute Deploy

### Step 1: Prepare Files (Already Done! ✓)
```bash
./prepare_deployment.sh
```

### Step 2: Create HF Space
1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Settings:
   - Space name: `80k-career-advisor` (or your choice)
   - SDK: **Gradio**
   - Hardware: **CPU basic** (free)
   - Visibility: Public or Private
4. Click **"Create Space"**

### Step 3: Add Secrets (CRITICAL!)
On your Space page → **Settings** → **Variables and Secrets**:

| Name | Value |
|------|-------|
| `QDRANT_URL` | Your Qdrant instance URL |
| `QDRANT_API_KEY` | Your Qdrant API key |
| `OPENAI_API_KEY` | Your OpenAI API key |

### Step 4: Upload Files

**Easy Way (Web Upload):**
1. Go to **Files and versions** tab
2. Click **"Upload files"**
3. Drag these 6 files from `hf_spaces_deploy/`:
   - app.py
   - rag_chat.py
   - citation_validator.py
   - config.py
   - requirements.txt
   - README.md
4. Click **"Commit changes to main"**

**Git Way:**
```bash
# Clone your new space
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# Copy files
cp ../80k_rag/hf_spaces_deploy/* .

# Push
git add .
git commit -m "Initial deployment"
git push
```

### Step 5: Wait & Test
- Build takes 2-5 minutes
- Your app will be live at: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
- Test with example questions!

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails | Check build logs, verify requirements.txt |
| "Module not found" | Ensure all dependencies in requirements.txt |
| No API response | Verify secrets are set correctly |
| "No relevant sources" | Check Qdrant instance is accessible |

## Cost

- **HF Space**: FREE (CPU basic tier)
- **OpenAI**: ~$0.01-0.05 per query
- **Qdrant**: FREE (up to 1GB)

Total: Essentially free for moderate usage!

## Need Help?

See detailed guides:
- `HF_SPACES_CHECKLIST.md` - Complete checklist
- `DEPLOYMENT.md` - Detailed deployment guide
- `README.md` - Full project documentation

