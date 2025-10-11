import gradio as gr
import os
from query import ask

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
            # Replace markdown bullets with bullet character for display in quote block
            display_text = display_text.replace('\n- ', '\n• ')
            if display_text.startswith('- '):
                display_text = '\n• ' + display_text[2:]
            citations_text += f"**[{i}]** {citation['title']}\n\n"
            citations_text += f"> \"{display_text}\"\n\n"
            citations_text += f"🔗 [View highlighted quote on 80,000 Hours →]({citation['url']})\n\n"
    
    # Add validation warnings if any
    if result.get("validation_errors"):
        citations_text += "\n---\n\n### ⚠️ Validation Warnings\n\n"
        for error in result["validation_errors"]:
            fuzzy_score = error.get('fuzzy_match_score', 0)
            citations_text += f"**[{error['citation_id']}]** {error['reason']}\n\n"
            
            # Format claimed quote (stored as 'quote' in validation result)
            claimed_quote = error.get('quote', '')
            claimed_quote = claimed_quote.replace('\n- ', '\n• ')
            if claimed_quote.startswith('- '):
                claimed_quote = '\n• ' + claimed_quote[2:]
            citations_text += f"**AI's claimed quote:**\n> \"{claimed_quote}\"\n\n"
            
            # Format matched text from source
            if error.get('matched_text'):
                matched_text = error['matched_text']
                matched_text = matched_text.replace('\n- ', '\n• ')
                if matched_text.startswith('- '):
                    matched_text = '\n• ' + matched_text[2:]
                citations_text += f"**Closest match in actual source** ({fuzzy_score:.1f}% fuzzy match):\n> \"{matched_text}\"\n\n"
    
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
            examples = [
                "What skills will be most in demand in the next 5–10 years?",
                "What careers will be most affected by AI?",
                "How can I work on the world’s most pressing problems?",
                "How do I figure out what I want to do with my life?",
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
