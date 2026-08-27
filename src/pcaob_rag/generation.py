"""Grounded prompting and optional Gemini answer generation."""

from __future__ import annotations

import os
import time
from collections.abc import Iterable, Mapping

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
REFUSAL_TEXT = (
    "The selected PCAOB inspection reports do not provide enough "
    "information to answer that question."
)

RETRYABLE_ERROR_MARKERS = (
    "429",
    "RESOURCE_EXHAUSTED",
    "503",
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
)


def _result_rows(results) -> Iterable[Mapping]:
    if hasattr(results, "to_dict"):
        return results.to_dict(orient="records")
    return results


def build_grounded_prompt(question: str, results) -> str:
    """Create a source-bounded prompt with exact citation requirements."""

    context_blocks = [
        f'SOURCE {row["citation"]}\n{row["text"]}'
        for row in _result_rows(results)
    ]
    context = "\n\n".join(context_blocks)
    return f"""You are an audit training assistant for junior auditors.

Answer the QUESTION using only the SOURCE EXCERPTS below.

Rules:
1. Do not use outside knowledge or invent issuer identities, amounts, findings, or audit procedures.
2. Put an exact supplied bracketed citation after every sentence or bullet containing a factual claim.
3. Use only citation labels that appear in the SOURCE EXCERPTS.
4. Explain supported findings in concise, clear coaching language.
5. If the excerpts do not directly provide the requested information, reply with exactly this sentence and nothing else:
   {REFUSAL_TEXT}
6. If asked to rank Deloitte and EY or judge either firm's overall audit quality from these selected inspections, use the exact refusal sentence.
7. Do not treat selected PCAOB inspections as representative ratings of an entire firm.

QUESTION:
{question}

SOURCE EXCERPTS:
{context}
"""


class GeminiGenerator:
    """Thin Gemini client wrapper that does not retain Interaction objects."""

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL) -> None:
        if not api_key:
            raise ValueError("A Gemini API key is required for live generation.")
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    @classmethod
    def from_environment(cls) -> "GeminiGenerator":
        """Load credentials from environment variables without storing them."""

        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip(),
        )

    def call(self, prompt: str, max_retries: int = 4) -> str:
        """Call Gemini with bounded exponential backoff."""

        for attempt in range(max_retries):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    input=prompt,
                    store=False,
                )
                answer = (interaction.output_text or "").strip()
                if not answer:
                    raise RuntimeError("Gemini returned an empty answer.")
                return answer
            except Exception as exc:
                is_retryable = any(
                    marker in str(exc) for marker in RETRYABLE_ERROR_MARKERS
                )
                if not is_retryable or attempt == max_retries - 1:
                    raise
                time.sleep(min(15 * (2**attempt), 60))
        raise RuntimeError("Gemini generation failed unexpectedly.")

    def answer(self, question: str, results) -> str:
        """Generate one answer from retrieved excerpts."""

        return self.call(build_grounded_prompt(question, results))

