import re

import gradio as gr
from dotenv import load_dotenv

from implementation.answer import answer_question
from implementation.evidence_highlighter import highlight_context

load_dotenv()


def is_in_scope(query: str) -> bool:
    q = query.lower()

    # Normalize common spelling variation/typo.
    q = q.replace("manfacturer", "manufacturer")

    ai_act_terms = {
        "ai act",
        "artificial intelligence act",
        "regulation (eu) 2024/1689",
        "regulation 2024/1689",
        "article",
        "recital",
        "annex",
        "high-risk",
        "high risk",
        "prohibited",
        "prohibited practice",
        "provider",
        "deployer",
        "importer",
        "distributor",
        "manufacturer",
        "product manufacturer",
        "operator",
        "general-purpose ai",
        "general purpose ai",
        "gpai",
        "transparency",
        "risk management",
        "conformity assessment",
        "fundamental rights",
        "human oversight",
        "technical documentation",
        "data governance",
        "market surveillance",
        "notified body",
        "ai literacy",
        "deepfake",
        "biometric",
        "emotion recognition",
        "social scoring",
        "regulatory sandbox",
        "penalty",
        "penalties",
        "fine",
        "fines",
    }

    return any(term in q for term in ai_act_terms)


def format_context(context, answer):
    result = "<h2 style='color: #ff7800;'>Retrieved EU AI Act Context</h2>\n\n"

    for doc in context:
        result += (
            f"<span style='color: #ff7800;'>"
            f"Source: {doc.metadata['source']}"
            f"</span>\n\n"
        )

        content = doc.page_content

        # Keep Markdown headings readable in the context panel.
        content = re.sub(
            r"^#{1,6}\s+(.+)$",
            r"\1",
            content,
            flags = re.MULTILINE,
        )

        # Highlight only the strongest sentences in this source.
        content = highlight_context(
            content,
            answer,
            max_sentences = 2,
        )

        result += content + "\n\n"

    return result


def chat(history):
    last_message = history[-1]["content"]
    prior = history[:-1]

    if not is_in_scope(last_message):
        history.append(
            {
                "role": "assistant",
                "content": (
                    "This system is limited to questions about the EU AI Act "
                    "(Regulation (EU) 2024/1689). Please ask a question within "
                    "that scope."
                ),
            }
        )

        return (
            history,
            "*No EU AI Act context retrieved because the question was outside "
            "the supported scope.*",
        )

    answer, context = answer_question(last_message, prior)
    history.append({"role": "assistant", "content": answer})

    return history, format_context(context, answer)


def main():
    def put_message_in_chatbot(message, history):
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title = "EU AI Act RAG Assistant", theme = theme) as ui:
        gr.Markdown(
            "# EU AI Act RAG Assistant\n"
            "Ask questions about Regulation (EU) 2024/1689.\n\n"
        )

        with gr.Row():
            with gr.Column(scale = 1):
                chatbot = gr.Chatbot(
                    label = "💬 Conversation", height = 600, type = "messages", show_copy_button = True
                )
                message = gr.Textbox(
                    label = "Your Question",
                    placeholder = "Ask anything about the EU AI Act...",
                    show_label = False,
                )

            with gr.Column(scale = 1):
                context_markdown = gr.Markdown(
                    label = "📚 Retrieved Context",
                    value = "*Retrieved context will appear here*",
                    container = True,
                    height = 600,
                )

        message.submit(
            put_message_in_chatbot, inputs = [message, chatbot], outputs = [message, chatbot]
        ).then(chat, inputs = chatbot, outputs = [chatbot, context_markdown])

    ui.launch(
        server_name = "0.0.0.0",
        server_port = 7860,
    )


if __name__ == "__main__":
    main()
