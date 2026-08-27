"""Transparent TF-IDF and optional semantic retrieval."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def infer_question_scope(question: str) -> tuple[list[str] | None, list[int] | None]:
    """Infer firm and inspection-year filters from a natural-language question."""

    firms: list[str] = []
    if re.search(r"\bDeloitte\b", question, flags=re.IGNORECASE):
        firms.append("Deloitte")
    if re.search(r"\bEY\b", question, flags=re.IGNORECASE) or re.search(
        r"Ernst\s*&?\s*Young", question, flags=re.IGNORECASE
    ):
        firms.append("EY")

    broad_scope = re.search(
        r"across (?:the )?selected reports|all selected reports|both firms",
        question,
        flags=re.IGNORECASE,
    )
    if broad_scope and not firms:
        firms = ["Deloitte", "EY"]

    if re.search(r"2022\s*[-–]\s*2024", question):
        years = [2022, 2023, 2024]
    else:
        years = sorted(
            {int(year) for year in re.findall(r"\b20(?:22|23|24)\b", question)}
        )
    return firms or None, years or None


class Retriever:
    """Search a chunk corpus using TF-IDF or semantic embeddings."""

    def __init__(
        self,
        chunks: pd.DataFrame | Sequence[dict],
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self.chunks = pd.DataFrame(chunks).reset_index(drop=True).copy()
        required = {"text", "firm_short", "inspection_year", "citation"}
        missing = required - set(self.chunks.columns)
        if missing:
            raise ValueError(f"Chunk corpus is missing columns: {sorted(missing)}")

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.chunks["text"])
        self.embedding_model_name = embedding_model_name
        self._semantic_model = None
        self._semantic_embeddings: np.ndarray | None = None

    def _ensure_semantic_index(self) -> None:
        if self._semantic_embeddings is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._semantic_model = SentenceTransformer(self.embedding_model_name)
        self._semantic_embeddings = self._semantic_model.encode(
            self.chunks["text"].tolist(),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def score_all_chunks(self, question: str, method: str = "semantic") -> np.ndarray:
        """Score every chunk against a question."""

        if method == "tfidf":
            question_vector = self.vectorizer.transform([question])
            return cosine_similarity(question_vector, self.tfidf_matrix).ravel()
        if method == "semantic":
            self._ensure_semantic_index()
            question_embedding = self._semantic_model.encode(
                [question],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0]
            return self._semantic_embeddings @ question_embedding
        raise ValueError("method must be 'tfidf' or 'semantic'")

    def _rank_filtered(
        self,
        question: str,
        *,
        k: int,
        method: str,
        firm: str | None = None,
        years: list[int] | None = None,
    ) -> pd.DataFrame:
        candidates = self.chunks.copy()
        candidates["similarity_score"] = self.score_all_chunks(question, method)
        if firm:
            candidates = candidates[
                candidates["firm_short"].str.casefold() == firm.casefold()
            ]
        if years:
            candidates = candidates[candidates["inspection_year"].isin(years)]

        return (
            candidates.sort_values("similarity_score", ascending=False)
            .drop_duplicates(subset=["citation"])
            .head(k)
            .reset_index(drop=True)
        )

    def retrieve(
        self,
        question: str,
        *,
        k: int = 6,
        method: str = "semantic",
    ) -> pd.DataFrame:
        """Retrieve cited pages, balancing cross-firm questions by firm."""

        firms, years = infer_question_scope(question)
        if firms and len(firms) > 1:
            per_firm = math.ceil(k / len(firms))
            firm_results: list[pd.DataFrame] = []
            for firm in firms:
                result = self._rank_filtered(
                    question,
                    k=per_firm,
                    method=method,
                    firm=firm,
                    years=years,
                ).copy()
                result["within_firm_rank"] = np.arange(1, len(result) + 1)
                firm_results.append(result)

            combined = pd.concat(firm_results, ignore_index=True)
            return (
                combined.sort_values(
                    ["within_firm_rank", "firm_short"],
                    ascending=[True, True],
                )
                .head(k)
                .drop(columns=["within_firm_rank"])
                .reset_index(drop=True)
            )

        firm = firms[0] if firms else None
        return self._rank_filtered(
            question,
            k=k,
            method=method,
            firm=firm,
            years=years,
        )

