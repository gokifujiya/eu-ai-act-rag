from __future__ import annotations

import re


STOPWORDS = {
    "according", "article", "articles", "regulation",
    "source", "sources", "reference", "references",
    "that", "this", "with", "from", "where", "which",
    "shall", "have", "been", "into", "their", "there",
    "under", "about", "also", "than", "when", "would",
    "could", "should", "such", "does", "were", "they",
}


def _terms(text: str) -> set[str]:
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{3,}\b", text.lower())
    return {word for word in words if word not in STOPWORDS}


def _sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """
    Return sentence positions from the ORIGINAL text so that
    highlighting does not lose Markdown formatting or whitespace.
    """
    spans = []

    pattern = re.compile(
        r"[^.!?]+(?:[.!?]+|$)",
        flags = re.MULTILINE,
    )

    for match in pattern.finditer(text):
        sentence = match.group(0)
        cleaned = re.sub(r"\s+", " ", sentence).strip()

        if len(cleaned) >= 40:
            spans.append((match.start(), match.end(), sentence))

    return spans


def highlight_context(
    text: str,
    answer: str,
    max_sentences: int = 2,
) -> str:
    """
    Highlight the strongest answer-relevant sentences while
    preserving the original retrieved text.
    """
    answer_terms = _terms(answer)

    if not answer_terms:
        return text

    candidates = []

    for start, end, sentence in _sentence_spans(text):
        sentence_terms = _terms(sentence)

        if not sentence_terms:
            continue

        overlap = sentence_terms & answer_terms

        if not overlap:
            continue

        score = len(overlap) / len(sentence_terms)

        candidates.append((score, start, end))

    candidates.sort(key = lambda item: item[0], reverse = True)
    selected = candidates[:max_sentences]

    # Work backwards so inserting HTML does not change
    # the positions of earlier sentences.
    selected.sort(key = lambda item: item[1], reverse = True)

    result = text

    for _, start, end in selected:
        original = result[start:end]

        highlighted = (
            "<span style=\"background-color: #fff3a3; "
            "padding: 2px 1px;\">"
            + original
            + "</span>"
        )

        result = result[:start] + highlighted + result[end:]

    return result
