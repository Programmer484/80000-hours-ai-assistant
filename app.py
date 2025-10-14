import gradio as gr
import os
from query import ask

print("🚀 Starting 80,000 Hours RAG system...")
from query import is_model_ready
print("✅ App ready! Model loading in background...")

def chat_interface(message: str, history):
    """Process question and return formatted response for chatbot.
    
    Args:
        message: User's question (string or dict with 'content' key)
        history: Chat history (list of message dicts with 'role' and 'content')
        
    Returns:
        Formatted response with answer and citations
    """
    # Handle both string and dict message formats
    if isinstance(message, dict):
        message = message.get('text', message.get('content', ''))
    
    if not message or not message.strip():
        return ""
    
    result = ask(message, show_context=False)
    
    # Format response: answer first, then divider, then citations
    response = result["answer"]
    
    # Add citations after divider
    if result["citations"]:
        response += "\n\n---\n\n**Citations:**\n\n"
        for i, citation in enumerate(result["citations"], 1):
            # Replace bullet points in citation text with newline + bullet icon
            response += f"**[{i}]** [{citation['title']}]({citation['url']})\n\n"
    
    return response


# --- Build Gradio UI ---
with gr.Blocks(title="80,000 Hours Q&A", theme=gr.themes.Soft(), css="""
    footer {display: none !important;}
    .examples button {
        background: linear-gradient(to bottom, #ffffff, #f8f9fa) !important;
        border: 2px solid #dee2e6 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease !important;
    }
    .examples button:hover {
        border-color: #adb5bd !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
        transform: translateY(-1px) !important;
    }
""") as demo:
    # Title section
    gr.Markdown("# 80,000 Hours Q&A")
    gr.Markdown("*Ask questions about career planning and get answers backed by citations from 80,000 Hours articles.*")
    
    gr.ChatInterface(
        fn=chat_interface,
        type="messages",
        chatbot=gr.Chatbot(
            height=400,
            show_copy_button=True,
            render_markdown=True,
            layout="bubble",
            type="messages"
        ),
        textbox=gr.MultimodalTextbox(
            placeholder="Ask about career planning...",
            show_label=False,
            submit_btn=True,
            sources=[]
        ),
        examples=[
            "What skills will be most in demand in the next 5–10 years?",
            "How can I work on the world's most pressing problems?",
            "How do I figure out what I want to do with my life?",
        ]
    )

# --- Launch Logic ---
if __name__ == "__main__":
    # Detect if running on Hugging Face Spaces (or other managed env)
    in_spaces = os.environ.get("SPACE_ID") is not None or os.environ.get("SYSTEM") == "spaces"

    if in_spaces:
        demo.launch()  # Use platform defaults
    else:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
