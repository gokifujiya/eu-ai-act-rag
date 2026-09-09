import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    convert_to_messages,
)
from langchain_core.documents import Document
from dotenv import load_dotenv


load_dotenv(override=True)

MODEL = "gpt-4.1-nano"

BASE_DIR = Path(__file__).parent.parent
DB_NAME = str(BASE_DIR / "vector_db")
KNOWLEDGE_BASE = BASE_DIR / "knowledge-base"

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

RETRIEVAL_K = 10

SYSTEM_PROMPT = """
You are an assistant answering questions about Regulation (EU) 2024/1689
(the EU Artificial Intelligence Act).

Answer the user's question using only the provided context.

Rules:
1. Base your answer only on the provided EU AI Act context.
2. Do not invent or assume legal provisions that are not supported by the context.
3. At the beginning of the answer, explicitly identify the main relevant legal
   provision using its exact identifier, for example:
   "According to Article 113..."
   "According to Recital 47..."
   "According to Annex III..."
4. If several provisions are relevant, identify the most important one first
   and mention the others where appropriate.
5. Clearly distinguish the general rule from exceptions, conditions, and
   special cases.
6. If the provided context is insufficient to answer the question, say that
   the answer cannot be determined from the provided EU AI Act materials.
7. Do not present the answer as legal advice.

Context:
{context}
"""


vectorstore = Chroma(
    persist_directory=DB_NAME,
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(
    search_kwargs={"k": RETRIEVAL_K}
)

llm = ChatOpenAI(
    temperature=0,
    model_name=MODEL
)


def fetch_context(question: str) -> list[Document]:
    """
    Retrieve relevant EU AI Act context documents for a question.
    """
    return retriever.invoke(question)


def combined_question(
    question: str,
    history: list[dict] = []
) -> str:
    """
    Combine previous user messages with the current question for retrieval.
    """
    prior = "\n".join(
        message["content"]
        for message in history
        if message["role"] == "user"
    )

    if prior:
        return prior + "\n" + question

    return question


def get_provision_text(question: str) -> str | None:
    """
    Return the full source text when a specific Article, Recital, or Annex
    is explicitly requested.
    """
    question = question.strip()

    # Article
    article_match = re.search(
        r"\bArticle\s+(\d{1,3})\b",
        question,
        re.IGNORECASE
    )

    if article_match:
        number = int(article_match.group(1))

        if 1 <= number <= 113:
            path = (
                KNOWLEDGE_BASE
                / "articles"
                / f"article_{number:03d}.md"
            )

            if path.exists():
                return path.read_text(encoding="utf-8")

    # Recital
    recital_match = re.search(
        r"\bRecital\s+(\d{1,3})\b",
        question,
        re.IGNORECASE
    )

    if recital_match:
        number = int(recital_match.group(1))

        if 1 <= number <= 180:
            path = (
                KNOWLEDGE_BASE
                / "recitals"
                / f"recital_{number:03d}.md"
            )

            if path.exists():
                return path.read_text(encoding="utf-8")

    # Annex
    annex_match = re.search(
        r"\bAnnex\s+([IVXLCDM]+)\b",
        question,
        re.IGNORECASE
    )

    if annex_match:
        annex_number = annex_match.group(1).upper()

        path = (
            KNOWLEDGE_BASE
            / "annexes"
            / f"annex_{annex_number}.md"
        )

        if path.exists():
            return path.read_text(encoding="utf-8")

    return None


def is_direct_provision_request(question: str) -> bool:
    """
    Detect requests such as:
    Article 6?
    Recital 47?
    Annex I?
    Show Article 6
    Full text of Annex III
    """
    question = question.strip()

    if re.fullmatch(
        r"(Article\s+\d{1,3}|Recital\s+\d{1,3}|Annex\s+[IVXLCDM]+)\s*[?.!]?",
        question,
        re.IGNORECASE
    ):
        return True

    request_phrases = [
        "show article",
        "show me article",
        "show recital",
        "show me recital",
        "show annex",
        "show me annex",
        "full text",
        "text of article",
        "text of recital",
        "text of annex",
        "display article",
        "display recital",
        "display annex",
    ]

    return any(
        phrase in question.lower()
        for phrase in request_phrases
    )


def answer_question(
    question: str,
    history: list[dict] = []
) -> tuple[str, list[Document]]:
    """
    Answer a question using either direct provision lookup or RAG.

    Returns:
        answer: generated or directly retrieved legal text
        docs: retrieved context documents used by the UI
    """

    # Direct Article / Recital / Annex lookup
    provision_text = get_provision_text(question)

    if provision_text and is_direct_provision_request(question):
        return provision_text, []

    # Normal RAG retrieval
    combined = combined_question(question, history)

    docs = fetch_context(combined)

    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', '')}\n"
        f"{doc.page_content}"
        for doc in docs
    )

    system_prompt = SYSTEM_PROMPT.format(
        context=context
    )

    messages = [
        SystemMessage(content=system_prompt)
    ]

    messages.extend(
        convert_to_messages(history)
    )

    messages.append(
        HumanMessage(content=question)
    )

    response = llm.invoke(messages)

    # Collect unique legal references
    sources = []

    for doc in docs:
        identifier = doc.metadata.get("identifier", "")
        title = doc.metadata.get("title", "")

        source = (
            f"{identifier} — {title}"
            if title
            else identifier
        )

        if source and source not in sources:
            sources.append(source)

    references = ""

    if sources:
        references = (
            "\n\n### References\n"
            + "\n".join(
                f"- {source}"
                for source in sources
            )
        )

    answer = response.content + references

    return answer, docs
