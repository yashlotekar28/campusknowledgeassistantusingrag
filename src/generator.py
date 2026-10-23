"""Gemini LLM generator with exponential backoff retry logic and grounding prompt."""

import time
from typing import Any, Dict, List, Optional
from src.config import config

try:
    from google import genai
except ImportError:
    genai = None

CAMPUS_PROMPT_TEMPLATE = """You are a helpful Campus Information Assistant for the institution.

Answer the question using only the evidence below.
Do not invent facts.
If the evidence is insufficient, say so honestly.
Use simple, clear, and student-friendly language.

EVIDENCE:
{context}

QUESTION:
{question}

ANSWER:
"""


class CampusAnswerGenerator:
    """Invokes Gemini LLM with grounded evidence and automatic retries."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.gemini_api_key
        self.model = model or config.gemini_model
        self.client = genai.Client(api_key=self.api_key) if (genai and self.api_key) else None

    def generate(self, question: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Format evidence and generate answer with retry logic."""
        if not self.client:
            return (
                "⚠️ GEMINI_API_KEY is not configured. Please add your key to .env or environment.\n\n"
                "Here is the retrieved context:\n"
                + "\n".join([f"- [Page {d['page_number']}] {d['text']}" for d in retrieved_docs])
            )

        context_parts = []
        for index, doc in enumerate(retrieved_docs, start=1):
            context_parts.append(
                f"[Evidence {index}]\n"
                f"Source: {doc['source']}\n"
                f"Page: {doc['page_number']}\n"
                f"Text: {doc['text']}"
            )
        context = "\n\n".join(context_parts)
        prompt = CAMPUS_PROMPT_TEMPLATE.format(context=context, question=question)

        response = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                break
            except Exception as error:
                error_message = str(error).upper()
                temporary_error = any(
                    code in error_message
                    for code in [
                        "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL"
                    ]
                )
                if not temporary_error or attempt == 2:
                    raise
                wait_seconds = 2 ** (attempt + 1)
                time.sleep(wait_seconds)

        answer = (response.text or "").strip() if response else ""
        if not answer:
            answer = "Gemini returned an empty answer. Please try again."
        return answer
