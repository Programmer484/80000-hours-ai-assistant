import gradio as gr
import os
from rag_chat import ask

def chat_interface(question: str, show_context: bool = False):
    """Process question and return formatted response."""
    if not question.strip():
        return "Please enter a question.", ""
    
    result = ask(question, show_context=show_context)
    
    # Format main response
    answer = result["answer"]
    
    # Format citations
    citations_text = ""
    if result["citations"]:
        citations_text += "\n\n---\n\n### 📚 Citations\n\n"
        for i, citation in enumerate(result["citations"], 1):
            # Use matched_text (actual source text) instead of AI's quote
            display_text = citation.get('matched_text', citation['quote'])
            citations_text += f"**[{i}]** {citation['title']}\n\n"
            citations_text += f"> \"{display_text}\"\n\n"
            citations_text += f"🔗 [View highlighted quote on 80,000 Hours →]({citation['url']})\n\n"
    
    # Add validation warnings if any
    if result.get("validation_errors"):
        citations_text += "\n⚠️ **Validation Warnings:**\n"
        for error in result["validation_errors"]:
            citations_text += f"- {error}\n"
    
    # Add stats
    if result["citations"]:
        valid_count = len([c for c in result["citations"] if c.get("validated", True)])
        total_count = len(result["citations"])
        citations_text += f"\n✓ {valid_count}/{total_count} citations validated"
    
    return answer, citations_text


# --- Build Gradio UI ---
with gr.Blocks(title="80,000 Hours Q&A", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎯 80,000 Hours Career Advice Q&A
        Ask questions about career planning and get answers backed by citations from 80,000 Hours articles.
        
        This RAG system retrieves relevant content from the 80,000 Hours knowledge base and generates answers with validated citations.
        """
    )

    with gr.Row():
        with gr.Column():
            question_input = gr.Textbox(
                label="Your Question",
                placeholder="e.g., Should I plan my entire career?",
                lines=2
            )
            show_context_checkbox = gr.Checkbox(
                label="Show retrieved context (for debugging)",
                value=False
            )
            submit_btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        with gr.Column():
            answer_output = gr.Textbox(
                label="Answer",
                lines=10,
                show_copy_button=True
            )

        with gr.Column():
            citations_output = gr.Markdown(label="Citations & Sources")

    # Event handlers
    submit_btn.click(
        fn=chat_interface,
        inputs=[question_input, show_context_checkbox],
        outputs=[answer_output, citations_output]
    )

    question_input.submit(
        fn=chat_interface,
        inputs=[question_input, show_context_checkbox],
        outputs=[answer_output, citations_output]
    )

    gr.Examples(
        examples=[
            "Should I plan my entire career?",
            "What career advice does 80k give?",
            "How can I have more impact with my career?",
            "What are the world's most pressing problems?",
        ],
        inputs=question_input
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
