"""Prompt templates for RAG compression and generation."""

SYSTEM_PROMPT = """
You are a helpful assistant that answers questions using the provided context. Cite the source identifiers.
If the context does not contain the answer, reply with "I don't know" and encourage the user to refresh the knowledge base.
""".strip()

COMPRESSION_PROMPT = """
Summarize the following chunks into structured facts and steps while preserving citated chunk ids:
{context}
""".strip()
