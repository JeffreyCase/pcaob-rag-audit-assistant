"""Convenience functions that connect corpus creation, retrieval, and generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .documents import build_corpus
from .generation import GeminiGenerator
from .retrieval import Retriever


def build_and_save_corpus(
    manifest_path: str | Path,
    raw_pdf_dir: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    """Create a corpus and save it locally; generated data is git-ignored."""

    chunks = build_corpus(manifest_path, raw_pdf_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks.to_csv(output_path, index=False)
    return chunks


def answer_question(
    question: str,
    chunks: pd.DataFrame,
    *,
    method: str = "semantic",
    k: int = 6,
) -> tuple[str, pd.DataFrame]:
    """Retrieve evidence and generate one optional live answer."""

    retriever = Retriever(chunks)
    evidence = retriever.retrieve(question, k=k, method=method)
    answer = GeminiGenerator.from_environment().answer(question, evidence)
    return answer, evidence

