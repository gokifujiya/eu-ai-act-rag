# EU AI Act RAG

A retrieval-augmented generation (RAG) system for answering questions about
Regulation (EU) 2024/1689, the European Union Artificial Intelligence Act.

The project uses the official text of the EU AI Act, structured into Articles,
Recitals, and Annexes, as its knowledge base.

## Architecture

User question
→ Hugging Face MiniLM embeddings
→ Chroma vector database
→ relevant EU AI Act chunks
→ OpenAI language model
→ answer with legal-source references

## Knowledge Base

The corpus contains:

- 113 Articles
- 180 Recitals
- 13 Annexes

The source text is derived from Regulation (EU) 2024/1689.

## Evaluation

The project includes a legal-domain evaluation framework covering:

- Mean Reciprocal Rank (MRR)
- nDCG
- keyword coverage
- answer accuracy
- completeness
- relevance
- legal-source accuracy

## Current Research Focus

The baseline dense-retrieval system works well for some direct legal questions,
such as application dates under Article 113.

More difficult questions involving long provisions distributed across multiple
chunks, such as Article 5 on prohibited AI practices, expose limitations of
flat dense retrieval.

Planned improvements include provision-aware retrieval, hybrid retrieval,
reranking, and legal structure-aware chunking.

## Disclaimer

This project is for research and educational purposes only and does not provide
legal advice.