"""Run one optional live query after building the local corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pcaob_rag.pipeline import answer_question

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="Question about the selected inspection reports")
    parser.add_argument(
        "--method",
        choices=("tfidf", "semantic"),
        default="semantic",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    corpus_path = ROOT / "data" / "processed" / "pcaob_revenue_chunks.csv"
    if not corpus_path.exists():
        raise SystemExit("Run `python scripts/build_corpus.py` first.")
    answer, sources = answer_question(
        args.question,
        pd.read_csv(corpus_path),
        method=args.method,
    )
    print(answer)
    print("\nRetrieved pages:")
    print(" | ".join(sources["citation"].tolist()))

