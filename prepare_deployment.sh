#!/bin/bash
# Helper script to prepare files for Hugging Face Spaces deployment

echo "📦 Preparing files for Hugging Face Spaces deployment..."
echo ""

# Create deployment directory
DEPLOY_DIR="hf_spaces_deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy necessary files
echo "Copying files..."
cp app.py $DEPLOY_DIR/
cp rag_chat.py $DEPLOY_DIR/
cp citation_validator.py $DEPLOY_DIR/
cp config.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/
cp README.md $DEPLOY_DIR/

echo "✅ Files copied to $DEPLOY_DIR/"
echo ""
echo "Files ready for deployment:"
ls -lh $DEPLOY_DIR/
echo ""
echo "📋 Next steps:"
echo "1. Create your Hugging Face Space at https://huggingface.co/spaces"
echo "2. Configure secrets (QDRANT_URL, QDRANT_API_KEY, OPENAI_API_KEY)"
echo "3. Clone your space: git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE"
echo "4. Copy files: cp hf_spaces_deploy/* YOUR_SPACE/"
echo "5. Push: cd YOUR_SPACE && git add . && git commit -m 'Initial deployment' && git push"
echo ""
echo "📖 See HF_SPACES_CHECKLIST.md for detailed instructions"

